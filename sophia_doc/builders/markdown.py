"""The Markdown Builder."""

from __future__ import annotations

import inspect
import warnings
from pathlib import Path
from textwrap import indent
from typing import Any

from docstring_parser import Docstring, DocstringParam, DocstringStyle
from typing_extensions import override

from sophia_doc import ClassNode, DataNode, DocNode, FunctionNode, ModuleNode
from sophia_doc.builders import Builder
from sophia_doc.utils import format_annotation, format_signature


def get_description(docstring: Docstring) -> list[str]:
    """Get description form a Docstring object.

    Args:
        docstring: A Docstring object.

    Returns:
        A list of description string.
    """
    result: list[str] = []
    if docstring.short_description:
        result.append(docstring.short_description)
    if docstring.long_description:
        result.append(docstring.long_description)
    return result


def parser_param(name: str, annotation: str | None, description: str | None) -> str:
    """Get formatted string of parameter.

    Args:
        name: Parameter name.
        annotation: Parameter annotation.
        description: Parameter description.

    Returns:
        Formatted string of parameter.
    """
    result = f"- {Markdown.bold(Markdown.escape(name))}"
    if annotation:
        result += f" ({Markdown.italic(Markdown.escape(annotation))})"
    if description:
        result += f" - {description}"
    return result


def parser_docstring_param(param: DocstringParam) -> str:
    """Get formatted string of parameter from a DocstringParam object.

    Args:
        param: A DocstringParam object.

    Returns:
        Formatted string of parameter.
    """
    return parser_param(param.arg_name, param.type_name, param.description)


class Markdown:
    """Markdown format."""

    @staticmethod
    def escape(text: str) -> str:
        """Escape Markdown control characters."""
        new_text = ""
        for c in text:
            if c in "*#\\()[]<>_`":
                new_text += "\\"
            new_text += c
        return new_text

    @staticmethod
    def indent(text: str, level: int = 1) -> str:
        """Indent."""
        return indent(text, prefix=" " * (level * 2))

    @staticmethod
    def italic(text: str) -> str:
        """Italic."""
        return f"_{text}_"

    @staticmethod
    def bold(text: str) -> str:
        """Bold."""
        return f"**{text}**"

    @staticmethod
    def title(text: str, level: int = 1) -> str:
        """Title."""
        return "#" * level + " " + text

    @staticmethod
    def inline_code(text: str) -> str:
        """Inline Code."""
        return f"`{text}`"


class MarkdownBuilder(Builder):
    """Markdown Builder.

    Attributes:
        anchor_extend: If true will add anchor extend to title,
            like # Your title {#your-custom-id}
        ignore_data: If true will ignore data in Markdown text.
    """

    anchor_extend: bool
    ignore_data: bool

    def __init__(
        self,
        module: ModuleNode,
        *,
        docstring_style: DocstringStyle = DocstringStyle.AUTO,
        anchor_extend: bool = False,
        ignore_data: bool = False,
    ) -> None:
        """Init Markdown Builder."""
        super().__init__(module, docstring_style=docstring_style)
        self.anchor_extend = anchor_extend
        self.ignore_data = ignore_data

    @override
    def _new_builder(self, module: ModuleNode) -> Builder:
        return self.__class__(
            module,
            docstring_style=self.docstring_style,
            anchor_extend=self.anchor_extend,
            ignore_data=self.ignore_data,
        )

    @override
    def get_path(
        self,
        exclude_module_name: bool = False,
        init_file_name: str = "index.md",
        **_kwagrs: Any,
    ) -> Path:
        """Get the path to write file.

        Args:
            exclude_module_name: If true will write file to path
                which exclude module name, like change output path
                form `./doc/sophia_doc/index.md` to `./doc/index.md`.
            init_file_name: The name of Markdown file
                from __init__.py, `index.md` by default.
        """
        if exclude_module_name:
            path = Path(*self.module.name.split(".")[1:])
        else:
            path = Path(*self.module.name.split(".")[0:])
        return (
            path / init_file_name if self.module.is_package else path.with_suffix(".md")
        )

    @override
    def text(self) -> str:
        """Get string of current module documentation."""
        result: list[str] = []
        result.append(Markdown.title(self.module.name, 1))

        docstring = self.get_docstring(self.module)
        result.extend(get_description(docstring))

        result.extend(self.build_doc(node) for node in self.module.attributes)

        return self._build_str(result) + "\n"

    @staticmethod
    def _build_str(str_list: list[str]) -> str:
        return "\n\n".join(filter(lambda x: x, str_list))

    def build_doc(self, node: DocNode[Any], *, level: int = 1, **kwargs: Any) -> str:
        """Build markdown string from a DocNode.

        Args:
            node: A DocNode.
            level: The title level.
            **kwargs: Other args.

        Returns:
            A markdown string.
        """
        if isinstance(node, ClassNode):
            return self.build_class(node, level=level, **kwargs)
        if isinstance(node, FunctionNode):
            return self.build_function(node, level=level, **kwargs)
        if isinstance(node, DataNode):
            return self.build_data(node, level=level, **kwargs)
        raise ValueError

    def _extend_title(self, title: str, node: DocNode[Any]) -> str:
        if not self.anchor_extend:
            return title
        anchor = node.qualname
        for c in "*#\\()[]<>_`.":
            anchor = anchor.replace(c, "-")
        return title + " {#" + anchor + "}"

    def build_class(self, node: ClassNode, *, level: int = 1, **_kwagrs: Any) -> str:
        """Build markdown string from a ClassNode.

        Args:
            node: A ClassNode.
            level: The title level.

        Returns:
            A markdown string.
        """
        _kind: list[str] = []
        if node.is_abstract:
            _kind.append("abstract")
        if isinstance(node.obj, Exception):
            _kind.append("exception")
        else:
            _kind.append("class")
        kind = " ".join(_kind)

        result: list[str] = []
        title = Markdown.title(
            Markdown.italic(kind) + " " + Markdown.inline_code(node.name), level + 1
        )
        result.append(self._extend_title(title, node))

        result.append("Bases: " + ", ".join(map(Markdown.inline_code, node.bases)))

        docstring = self.get_docstring(node)
        result.extend(get_description(docstring))

        if docstring.params or node.annotations:
            result.append("- **Attributes**")

            parma_dict: dict[
                str, tuple[inspect.Parameter | None, DocstringParam | None]
            ] = {}
            if node.annotations:
                parma_dict = {
                    key: (annotation, None)
                    for key, annotation in node.annotations.items()
                    if not key.startswith("_")
                }

            if docstring.params:
                for param_doc in docstring.params:
                    annotation, _ = parma_dict.get(param_doc.arg_name, (None, None))
                    if param_doc.type_name is None and annotation:
                        param_doc.type_name = format_annotation(
                            annotation, base_module=node.module.name
                        )
                    parma_dict[param_doc.arg_name] = (annotation, param_doc)

            for name, (annotation, param_doc) in parma_dict.items():
                if param_doc is None:
                    result.append(
                        Markdown.indent(
                            parser_param(
                                name,
                                annotation
                                and format_annotation(
                                    annotation, base_module=node.module.name
                                ),
                                None,
                            )
                        )
                    )
                else:
                    result.append(Markdown.indent(parser_docstring_param(param_doc)))

        if docstring.examples:
            result.append("- **Examples**")
            result.append(Markdown.indent(docstring.examples[0].description or ""))

        for _name, kind, node_ in node.attributes:
            result.append(
                self.build_doc(
                    node_,
                    level=level + 1,
                    kind=kind,
                    ignore_first_arg=kind in {"method", "class method"},
                )
            )

        return self._build_str(result)

    @staticmethod
    def _build_argument(
        node: FunctionNode, docstring: Docstring, *, ignore_first_arg: bool = False
    ) -> list[str]:
        result: list[str] = []
        if docstring.params or (node.signature and node.signature.parameters):
            parma_dict: dict[
                str, tuple[inspect.Parameter | None, DocstringParam | None]
            ] = {}
            if node.signature and node.signature.parameters:
                for _key, param in node.signature.parameters.items():
                    key = _key
                    if param.kind == param.VAR_POSITIONAL:
                        key = "*" + key
                    elif param.kind == param.VAR_KEYWORD:
                        key = "**" + key
                    parma_dict[key] = (param, None)

            if docstring.params:
                for param_doc in docstring.params:
                    if (
                        param_doc.arg_name not in parma_dict
                        and node.signature
                        and node.signature.parameters
                    ):
                        warnings.warn(
                            f'The argument "{param_doc.arg_name}" of {node.qualname} '
                            f"can not find in function signature.",
                            stacklevel=1,
                        )
                    param, _ = parma_dict.get(param_doc.arg_name, (None, None))
                    if param_doc.type_name is None and param:
                        param_doc.type_name = format_annotation(
                            param.annotation, base_module=node.module.name
                        )
                    parma_dict[param_doc.arg_name] = (param, param_doc)

            if ignore_first_arg and parma_dict:
                parma_dict.pop(next(iter(parma_dict.keys())))

            if parma_dict:
                result.append("- **Arguments**")

            for param, param_doc in parma_dict.values():
                if param_doc is not None:
                    result.append(Markdown.indent(parser_docstring_param(param_doc)))
                elif param is not None:
                    result.append(
                        Markdown.indent(
                            parser_param(
                                param.name,
                                format_annotation(
                                    param.annotation, base_module=node.module.name
                                ),
                                None,
                            )
                        )
                    )

        return result

    def build_function(
        self,
        node: FunctionNode,
        *,
        level: int = 1,
        kind: str = "function",
        ignore_first_arg: bool = False,
        **_kwagrs: Any,
    ) -> str:
        """Build markdown string from a FunctionNode.

        Args:
            node: A FunctionNode.
            level: The title level.
            kind: The function kind, like 'function', 'method', 'class method'.
            ignore_first_arg: If True the first argument of the function
                will be ignored.

        Returns:
            A markdown string.
        """
        if not node.signature:
            warnings.warn(
                f"The {node.qualname} ({node.obj}) not have signature, ignored.",
                stacklevel=1,
            )
            return ""

        _kind: list[str] = []
        if node.is_async:
            _kind.append("async")
        if node.is_lambda_func:
            _kind.append("lambda")
        _kind.append(kind)
        kind = " ".join(_kind)

        result: list[str] = []
        result.append(
            self._extend_title(
                Markdown.title(
                    Markdown.italic(kind)
                    + " "
                    + Markdown.inline_code(
                        f"{node.name}{format_signature(node.signature)}"
                    ),
                    level + 1,
                ),
                node,
            )
        )

        docstring = self.get_docstring(node)
        result.extend(get_description(docstring))

        result.extend(
            self._build_argument(node, docstring, ignore_first_arg=ignore_first_arg)
        )

        if (
            docstring.returns is not None
            or node.signature.return_annotation is not inspect.Signature.empty
        ):
            result.append("- **Returns**")

            type_name = ""
            if (
                docstring.returns is not None
                and docstring.returns.type_name is not None
            ):
                type_name = docstring.returns.type_name
            elif node.signature.return_annotation is not inspect.Signature.empty:
                type_name = format_annotation(
                    node.signature.return_annotation, base_module=node.module.name
                )

            if type_name:
                result.append(
                    Markdown.indent(
                        f"Type: {Markdown.italic(Markdown.escape(type_name))}"
                    )
                )

            if docstring.returns and docstring.returns.description:
                result.append(Markdown.indent(docstring.returns.description))

        if docstring.raises:
            result.append("- **Raises**")
            result.extend(
                Markdown.indent(
                    "- {type_name} - {description}".format(
                        type_name=Markdown.bold(
                            Markdown.escape(raise_doc.type_name or "")
                        ),
                        description=raise_doc.description,
                    )
                )
                for raise_doc in docstring.raises
            )

        if docstring.examples:
            result.append("- **Examples**")
            result.append(Markdown.indent(docstring.examples[0].description or ""))

        return self._build_str(result)

    def build_data(
        self,
        node: DataNode[Any],
        *,
        level: int = 1,
        kind: str = "data",
        **_kwagrs: Any,
    ) -> str:
        """Build markdown string from a DataNode.

        Args:
            node: A DataNode.
            level: The title level.
            kind: The function kind, like 'data', 'property'.

        Returns:
            A markdown string.
        """
        if self.ignore_data and kind == "data":
            return ""

        result: list[str] = []
        result.append(
            self._extend_title(
                Markdown.title(
                    Markdown.italic(kind) + " " + Markdown.inline_code(node.name),
                    level + 1,
                ),
                node,
            )
        )

        if "property" in kind and node.annotations.get("return", None):
            result.append(
                "Type: {type_name}".format(
                    type_name=Markdown.italic(
                        Markdown.escape(
                            format_annotation(
                                node.annotations["return"], base_module=node.module.name
                            )
                        )
                    )
                )
            )

        docstring = self.get_docstring(node)
        result.extend(get_description(docstring))

        return self._build_str(result)
