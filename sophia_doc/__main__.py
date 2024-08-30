"""The Sophia-doc Command-line interface."""

from __future__ import annotations

import argparse

from docstring_parser import DocstringStyle

from sophia_doc import ModuleNode
from sophia_doc.builders.markdown import MarkdownBuilder
from sophia_doc.utils import import_module

parser = argparse.ArgumentParser(
    description="Sophia_doc is a python package to automatically "
    "generate API documents for Python modules",
    formatter_class=argparse.ArgumentDefaultsHelpFormatter,
)
parser.add_argument("module", type=str, help="Python module names.")
parser.add_argument(
    "-o",
    "--output-dir",
    type=str,
    default="doc",
    help="The directory to write document.",
)
parser.add_argument(
    "-f",
    "--format",
    type=str,
    default="markdown",
    help="File format of document.",
)
parser.add_argument(
    "--docstring-style",
    type=str,
    default="auto",
    help="Docstring style the python module used.",
)
parser.add_argument(
    "--ignore-data",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Ignore data in Markdown text.",
)
parser.add_argument(
    "--anchor-extend",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Add anchor to markdown title.",
)
parser.add_argument(
    "--overwrite",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Overwrite any file in output directory.",
)
parser.add_argument(
    "--exclude-module-name",
    type=bool,
    action=argparse.BooleanOptionalAction,
    default=False,
    help="Write file to path which exclude module name.",
)
parser.add_argument(
    "--init-file-name",
    type=str,
    default="index.md",
    help="The name of Markdown file from __init__.py, index.md by default.",
)


def cli() -> None:
    """The Sophia-doc Command-line interface."""
    args = parser.parse_args()
    if args.format == "markdown":
        builder = MarkdownBuilder(
            ModuleNode(import_module(args.module)),
            docstring_style=getattr(DocstringStyle, args.docstring_style.upper()),
            anchor_extend=args.anchor_extend,
            ignore_data=args.ignore_data,
        )
    else:
        msg = "format argument must be 'markdown'"
        raise ValueError(msg)
    builder.write(
        args.output_dir,
        overwrite=args.overwrite,
        exclude_module_name=args.exclude_module_name,
        init_file_name=args.init_file_name,
    )


if __name__ == "__main__":
    cli()
