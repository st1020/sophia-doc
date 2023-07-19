"""Builder is class to build ModuleNode to target formats."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from docstring_parser import Docstring, DocstringStyle, parse

if TYPE_CHECKING:
    from sophia_doc import DocNode, ModuleNode


class Builder(ABC):
    """Base class of Builder.

    Builds target formats from ModuleNode.

    Attributes:
        module: A ModuleNode object.
        docstring_style: The docstring style the module used, auto check by default.
    """

    module: ModuleNode
    docstring_style: DocstringStyle

    def __init__(
        self,
        module: ModuleNode,
        *,
        docstring_style: DocstringStyle = DocstringStyle.AUTO,
    ):
        """Init Builder.

        Args:
            module: The Module Node to build.
            docstring_style: The docstring style. Defaults to DocstringStyle.AUTO.
        """
        self.module = module
        self.docstring_style = docstring_style

    def _new_builder(self, module: ModuleNode) -> Builder:
        """Get a new instance of Builder class, is used in write method."""
        return self.__class__(module, docstring_style=self.docstring_style)

    def get_docstring(self, obj: DocNode) -> Docstring:
        """Get the Docstring object of a DocNode object.

        Args:
            obj: A DocNode object.

        Returns:
            A Docstring object.
        """
        return parse(obj.docstring, style=self.docstring_style)

    @abstractmethod
    def text(self) -> str:
        """Get string of current module documentation."""
        raise NotImplementedError

    @abstractmethod
    def get_path(self, **kwargs) -> Path:
        """Get the path to write file."""
        raise NotImplementedError

    def write(self, output_dir: str, *, overwrite: bool = False, **kwargs) -> None:
        """Write file to output dir.

        Args:
            output_dir: The output directory.
            overwrite: If true will overwrite any file in output directory,
                otherwise raise an Exception when file already exists.
            **kwargs: Other args.
        """
        filepath = Path(output_dir).resolve() / self.get_path(**kwargs)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        if not self.module.is_namespace:
            filepath.touch(exist_ok=overwrite)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.text())
        for submodule in self.module.submodules:
            self._new_builder(submodule).write(
                output_dir, overwrite=overwrite, **kwargs
            )
