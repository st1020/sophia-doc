"""Sophia_doc is a tool to automatically generate API documents for Python modules.

Typical usage example:

```
import sophia_doc
import sophia_doc.builders.markdown

module = sophia_doc.ModuleNode(sophia_doc)
builder = sophia_doc.builders.markdown.MarkdownBuilder(module)
builder.write('doc_dir')
```
"""
from __future__ import annotations

import inspect
import pkgutil
import sys
import traceback
import types
import warnings
from enum import Enum
from functools import cached_property
from typing import Any, Generic, NamedTuple, TypeVar, Union

from sophia_doc.utils import import_module

_T = TypeVar("_T")


def _find_class(func: Any) -> type | None:
    # cut from pydoc
    cls = sys.modules.get(func.__module__)
    if cls is None:
        return None
    for name in func.__qualname__.split(".")[:-1]:
        cls = getattr(cls, name)
    if not inspect.isclass(cls):
        return None
    return cls


def _find_doc(obj: Any) -> str | None:
    # cut from pydoc
    if inspect.ismethod(obj):
        name = obj.__func__.__name__  # type: ignore
        self = obj.__self__
        if (
            inspect.isclass(self)
            and getattr(self, name, None).__func__ is obj.__func__  # type: ignore
        ):
            # class method
            cls = self
        else:
            cls = self.__class__
    elif inspect.isfunction(obj):
        name = obj.__name__
        cls = _find_class(obj)
        if cls is None or getattr(cls, name) is not obj:
            return None
    elif inspect.isbuiltin(obj):
        name = obj.__name__
        self = obj.__self__
        if inspect.isclass(self) and self.__qualname__ + "." + name == obj.__qualname__:
            # class method
            cls = self
        else:
            cls = self.__class__
    # Should be tested before isdatadescriptor().
    elif isinstance(obj, property):
        func = obj.fget
        name = func.__name__  # type: ignore
        cls = _find_class(func)
        if cls is None or getattr(cls, name) is not obj:
            return None
    elif inspect.ismethoddescriptor(obj) or inspect.isdatadescriptor(obj):
        name = obj.__name__  # type: ignore
        cls = obj.__objclass__  # type: ignore
        if getattr(cls, name) is not obj:
            return None
        if inspect.ismemberdescriptor(obj):
            slots = getattr(cls, "__slots__", None)
            if isinstance(slots, dict) and name in slots:
                return slots[name]
    else:
        return None
    for base in cls.__mro__:  # type: ignore
        try:
            doc = _get_own_doc(getattr(base, name))
        except AttributeError:
            continue
        if doc is not None:
            return doc
    return None


def _get_own_doc(obj: Any) -> str | None:
    """Get the documentation string for an object if it is not inherited from its class."""
    # cut from pydoc
    try:
        doc = object.__getattribute__(obj, "__doc__")
        if doc is None:
            return None
        if obj is not type:
            typedoc = type(obj).__doc__
            if isinstance(typedoc, str) and typedoc == doc:
                return None
    except AttributeError:
        return None
    else:
        return doc


def _getdoc(obj: Any):
    """Get the documentation string for an object.

    All tabs are expanded to space. To clean up docstrings that are
    indented to line up with blocks of code, any whitespace than can be
    uniformly removed from the second line onwards is removed.
    """
    # cut from pydoc
    doc = _get_own_doc(obj)
    if doc is None:
        try:
            doc = _find_doc(obj)
        except (AttributeError, TypeError):
            return None
    if not isinstance(doc, str):
        return None
    return inspect.cleandoc(doc)


def getdoc(obj: Any) -> str:
    """Get the docstring string or comments for an object."""
    # cut from pydoc
    result = _getdoc(obj) or inspect.getcomments(obj)
    return result or ""


def isdata(obj: object) -> bool:
    """Check if an object is of a type that probably means it's data."""
    # cut from pydoc
    return not (
        inspect.ismodule(obj)
        or inspect.isclass(obj)
        or inspect.isroutine(obj)
        or inspect.isframe(obj)
        or inspect.istraceback(obj)
        or inspect.iscode(obj)
    )


def is_visible_name(name: str, _all: list | None = None) -> bool:
    """Decide whether to show documentation on a variable.

    Args:
        name: The variable name.
        _all: __all__ list of a module.

    Returns:
        Show documentation on a variable or not.
    """
    if name == "__init__":
        return True
    # only document that which the programmer exported in __all__
    if _all is not None:
        return name in _all
    return not name.startswith("_")


def get_annotations(obj: Any) -> dict[str, Any]:
    """Get the annotations dict for an object."""
    # refs: https://docs.python.org/3/howto/annotations.html
    if sys.version_info >= (3, 10):
        return inspect.get_annotations(obj)
    if isinstance(obj, type):
        return obj.__dict__.get("__annotations__", {})
    return getattr(obj, "__annotations__", {})


class DocNode(Generic[_T]):
    """The base class of document node.

    Attributes:
        obj: An object.
        name: The name of this object.
        module: The module of this object.
    """

    __slots__ = ("obj", "name", "module", "_qualname")
    obj: _T
    name: str
    module: ModuleNode
    _qualname: str

    def __init__(self, obj: _T, name: str, qualname: str, module: ModuleNode):
        """Init DocNode."""
        self.obj = obj
        self.name = name
        self._qualname = qualname
        self.module = module

    @cached_property
    def qualname(self) -> str:
        """The qualname of this object."""
        return getattr(self.obj, "__qualname__", self._qualname)

    @cached_property
    def realname(self) -> str:
        """Real name of this object."""
        return getattr(self.obj, "__name__", self.name)

    @cached_property
    def annotations(self) -> dict[str, Any]:
        """Annotations of this object."""
        return get_annotations(self.obj)

    @cached_property
    def docstring(self) -> str:
        """Docstring of this object."""
        return getdoc(self.obj)

    @staticmethod
    def from_obj(obj: Any, name: str, qualname: str, module: ModuleNode) -> DocNode:
        """Returns an object of DocNode's subclass.

        Args:
            obj: An object.
            name: The name of the object.
            qualname: The qualname of the object.
            module: The module of the object.

        Returns:
            A DocNode object.
        """
        try:
            if inspect.ismodule(obj):
                return ModuleNode(obj)
            if inspect.isclass(obj):
                return ClassNode(obj, name, qualname, module)
            if inspect.isroutine(obj):
                return FunctionNode(obj, name, qualname, module)  # type: ignore
        except AttributeError:
            pass
        if isdata(obj):
            return DataNode(obj, name, qualname, module)
        return OtherNode(obj, name, qualname, module)

    def __repr__(self):
        """Return the repr of this DocNode."""
        return (
            f"{self.__class__.__name__}:{self.name} "
            f"obj:{self.obj} docstring:{self.docstring}"
        )


class ModuleNode(DocNode[types.ModuleType]):
    """The class of module node."""

    def __init__(self, obj: types.ModuleType):
        """Init ModuleNode."""
        super().__init__(obj, obj.__name__, "", self)

    @cached_property
    def attributes(self) -> list[DocNode]:
        """A list of attributes of this module."""
        _all = getattr(self.obj, "__all__", None)
        attributes = []
        for key, value in list(getattr(self.obj, "__dict__", {}).items()):
            if (inspect.getmodule(value) or self.obj) is self.obj and is_visible_name(
                key, _all
            ):
                attributes.append(self.from_obj(value, key, key, self))
        return attributes

    @cached_property
    def submodules(self) -> list[ModuleNode]:
        """A list of submodules of this module."""
        submodules = []
        submodule_names = set()
        if self.is_package:
            for _importer, modname, _ispkg in pkgutil.iter_modules(self.obj.__path__):
                if not is_visible_name(modname):
                    continue
                try:
                    submodule_names.add(modname)
                    module = import_module(self.name + "." + modname)
                    submodules.append(ModuleNode(module))
                except ImportError:
                    warnings.warn(
                        f"Can not import {modname}:\n{traceback.format_exc()}",
                        stacklevel=1,
                    )

        for key, value in inspect.getmembers(self.obj, inspect.ismodule):
            if (
                value.__name__.startswith(self.name + ".")
                and key not in submodule_names
            ):
                submodules.append(ModuleNode(value))
        return submodules

    @cached_property
    def file(self) -> str | None:
        """The source file name of this module."""
        try:
            return inspect.getabsfile(self.obj)
        except TypeError:
            return None

    @cached_property
    def source(self) -> str | None:
        """The source of this module."""
        loader = getattr(self.obj, "__loader__", None)
        if loader and getattr(loader, "get_source", None):
            try:
                source = loader.get_source(self.name)
                if source:
                    return source
            except ImportError:
                pass
        try:
            return inspect.getsource(self.obj)
        except OSError:
            return None

    @cached_property
    def is_package(self) -> bool:
        """Returns True if this module is a package."""
        return hasattr(self.obj, "__path__")

    @cached_property
    def is_namespace(self) -> bool:
        """Returns True if this module is a namespace package."""
        return hasattr(self.obj, "__path__") and not hasattr(self.obj, "__file__")

    @cached_property
    def classes(self) -> list[ClassNode]:
        """A list of class objects in this module's attributes."""
        return [i for i in self.attributes if isinstance(i, ClassNode)]

    @cached_property
    def functions(self) -> list[FunctionNode]:
        """A list of function objects in this module's attributes."""
        return [i for i in self.attributes if isinstance(i, FunctionNode)]

    @cached_property
    def data(self) -> list[DataNode]:
        """A list of data objects in module's this attributes."""
        return [i for i in self.attributes if isinstance(i, DataNode)]


class ClassNode(DocNode[type]):
    """The class of class node."""

    class Attribute(NamedTuple):
        """The attribute of a class."""

        name: str
        kind: str
        node: DocNode

    @cached_property
    def attributes(self) -> list[ClassNode.Attribute]:
        """A list of attributes of this class."""
        attributes = []
        for name in filter(is_visible_name, dir(self.obj)):
            if isinstance(self.obj, Enum) and name == "__init__":
                continue

            if (
                name != "__init__"
                and name not in self.obj.__dict__
                and name not in getattr(self.obj, "__slots__", [])
            ):
                continue

            value = getattr(self.obj, name)

            if isinstance(value, (staticmethod, types.BuiltinMethodType)):
                kind = "static method"
            elif isinstance(value, (classmethod, types.ClassMethodDescriptorType)):
                kind = "class method"
            elif isinstance(value, property):
                kind = "readonly property" if value.fset is None else "property"
            elif inspect.isroutine(value):
                kind = "method"
            elif inspect.isdatadescriptor(value):
                # ignore data descriptor create by __slots__
                if name in getattr(self.obj, "__slots__", []):
                    continue
                kind = "data descriptor"
            else:
                kind = "data"

            # get original function from class method or static method
            if kind == "class method" or kind == "static method":
                value = value.__func__  # type: ignore

            # functools.cached_property needs special handling
            if isinstance(value, cached_property):
                kind = "cached property"
                node = DataNode(value, name, self.qualname + "." + name, self.module)
            else:
                node = DocNode.from_obj(
                    value, name, self.qualname + "." + name, self.module
                )

            attributes.append(self.Attribute(name, kind, node))

        return attributes

    @cached_property
    def subclasses(self) -> list[ClassNode]:
        """A list of subclasses of this class."""
        return [
            ClassNode(cls, cls.__name__, cls.__qualname__, self.module)
            for cls in type.__subclasses__(self.obj)
            if not (cls.__name__.startswith("_") and cls.__module__ == "builtins")
        ]

    @cached_property
    def bases(self) -> tuple[str, ...]:
        """Base class names of this class."""
        return tuple(
            (x.__module__ + "." if x.__module__ != "builtins" else "") + x.__qualname__
            for x in self.obj.__bases__
        )

    @cached_property
    def mro(self) -> tuple[type, ...]:
        """The mro of this class."""
        return inspect.getmro(self.obj)

    @cached_property
    def is_abstract(self) -> bool:
        """Returns True if this class is an abstract class."""
        return inspect.isabstract(self.obj)


class FunctionNode(
    DocNode[Union[types.FunctionType, types.MethodType, types.MethodDescriptorType]]
):
    """The class of function node."""

    @cached_property
    def signature(self) -> inspect.Signature | None:
        """Signature of this function."""
        try:
            return inspect.signature(self.obj)
        except (ValueError, TypeError):
            return None

    @cached_property
    def is_async(self) -> bool:
        """Returns True if this function is an async function."""
        return inspect.iscoroutinefunction(self.obj) or inspect.isasyncgenfunction(
            self.obj
        )

    @cached_property
    def is_bound_method(self) -> bool:
        """Returns True if this function is a bound method."""
        if inspect.ismethod(self.obj):
            return True
        if inspect.isbuiltin(self.obj):
            _self = getattr(self.obj, "__self__", None)
            return not (inspect.ismodule(_self) or (_self is None))
        return False

    @cached_property
    def is_lambda_func(self):
        """Returns True if this function is a lambda function."""
        return self.realname == "<lambda>"


class DataNode(DocNode[_T]):
    """The class of data node."""

    @cached_property
    def annotations(self) -> dict[str, Any]:
        """Annotations of this object."""
        if isinstance(self.obj, property):
            return get_annotations(self.obj.fget)
        if isinstance(self.obj, cached_property):
            return get_annotations(self.obj.func)
        return get_annotations(self.obj)


class OtherNode(DocNode[_T]):
    """The class of other node."""
