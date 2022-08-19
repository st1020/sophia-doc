"""Utils of sophia_doc."""
import re
import inspect
import warnings
import importlib
import traceback
from types import ModuleType
from typing import Any, Optional


def import_module(modname: str) -> ModuleType:
    """A wrapper of importlib.import_module, convert exceptions to ImportError.

    Args:
        modname: The name of the module to be imported.

    Returns:
        The imported module.
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=ImportWarning)
            return importlib.import_module(modname)
    except BaseException as exc:
        if isinstance(exc, KeyboardInterrupt):
            # Dot not catch KeyboardInterrupt.
            # Catch KeyboardInterrupt may prevent user kill python
            # when the module took a too long time to import.
            raise exc
        raise ImportError(exc, traceback.format_exc()) from exc


def format_annotation(annotation: Any, base_module: Optional[ModuleType] = None) -> str:
    """Format the annotation.

    Args:
        annotation: The annotation object to be formatted.
        base_module: A module which the object from.

    Returns:
        The formatted annotation.
    """
    if annotation is inspect.Signature.empty:
        return ""
    if isinstance(annotation, str):
        return annotation
    # use regex delete 'ForwardRef' from annotation
    return re.sub(
        r"\bForwardRef\((?P<quot>[\'\"])(?P<string>.*?)(?P=quot)\)",
        r"\g<string>",
        inspect.formatannotation(annotation, base_module),
    )


def format_parameter(parameter: inspect.Parameter, type_comments: bool = False) -> str:
    """Format inspect.Parameter object, type comments is optional.

    Cut from inspect.Parameter.__str__().

    Args:
        parameter: The inspect.Parameter object to be formatted.
        type_comments: If True will include type comments.

    Returns:
        The formatted string.
    """
    kind = parameter.kind
    formatted = parameter.name

    # Add annotation and default value
    if parameter.annotation is not inspect.Parameter.empty and type_comments:
        formatted = "{}: {}".format(formatted, format_annotation(parameter.annotation))

    if parameter.default is not inspect.Parameter.empty:
        if parameter.annotation is not inspect.Parameter.empty:
            formatted = "{} = {}".format(formatted, repr(parameter.default))
        else:
            formatted = "{}={}".format(formatted, repr(parameter.default))

    if kind == inspect.Parameter.VAR_POSITIONAL:
        formatted = "*" + formatted
    elif kind == inspect.Parameter.VAR_KEYWORD:
        formatted = "**" + formatted

    return formatted


def format_signature(signature: inspect.Signature, type_comments: bool = False) -> str:
    """
    Format inspect.Signature object, type comments is optional.

    Cut from inspect.Signature.__str__().

    Args:
        signature: The inspect.Signature object to be formatted.
        type_comments: If True will include type comments.

    Returns:
        The formatted string.
    """
    if type_comments:
        return str(signature)

    result = []
    render_pos_only_separator = False
    render_kw_only_separator = True
    for param in signature.parameters.values():
        formatted = format_parameter(param, type_comments=type_comments)

        kind = param.kind

        if kind == inspect.Parameter.POSITIONAL_ONLY:
            render_pos_only_separator = True
        elif render_pos_only_separator:
            # It's not a positional-only parameter, and the flag
            # is set to 'True' (there were pos-only params before.)
            result.append("/")
            render_pos_only_separator = False

        if kind == inspect.Parameter.VAR_POSITIONAL:
            # OK, we have an '*args'-like parameter, so we won't need
            # a '*' to separate keyword-only arguments
            render_kw_only_separator = False
        elif kind == inspect.Parameter.KEYWORD_ONLY and render_kw_only_separator:
            # We have a keyword-only parameter to render, and we haven't
            # rendered an '*args'-like parameter before, so add a '*'
            # separator to the parameters list ("foo(arg1, *, arg2)" case)
            result.append("*")
            # This condition should be only triggered once, so
            # reset the flag
            render_kw_only_separator = False

        result.append(formatted)

    if render_pos_only_separator:
        # There were only positional-only parameters, hence the
        # flag was not reset to 'False'
        result.append("/")

    rendered = "({})".format(", ".join(result))

    if signature.return_annotation is not inspect.Parameter.empty and type_comments:
        anno = format_annotation(signature.return_annotation)
        rendered += " -> {}".format(anno)

    return rendered
