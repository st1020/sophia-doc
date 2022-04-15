import argparse

from docstring_parser import DocstringStyle

from sophia_doc import ModuleNode
from sophia_doc.utils import import_module
from sophia_doc.builders.markdown import MarkdownBuilder

parser = argparse.ArgumentParser(
    description='Sophia_doc is a python package to automatically generate API documents for Python modules',
    formatter_class=argparse.ArgumentDefaultsHelpFormatter
)
parser.add_argument('module',
                    type=str,
                    help='Python module names.')
parser.add_argument('-o',
                    '--output-dir',
                    type=str,
                    default='doc',
                    help='The directory to write document.')
parser.add_argument('--docstring-style',
                    type=str,
                    default='auto',
                    help='Docstring style the python module used.')
parser.add_argument('--anchor-extend',
                    type=bool,
                    action=argparse.BooleanOptionalAction,
                    default=False,
                    help='Add anchor to markdown title.')
parser.add_argument('--overwrite',
                    type=bool,
                    action=argparse.BooleanOptionalAction,
                    default=False,
                    help='Overwrite any file in output directory.')
parser.add_argument('--exclude-module-name',
                    type=bool,
                    action=argparse.BooleanOptionalAction,
                    default=False,
                    help='Write file to path which exclude module name.')

if __name__ == '__main__':
    args = parser.parse_args()
    MarkdownBuilder(
        ModuleNode(import_module(args.module)),
        docstring_style=getattr(DocstringStyle, args.docstring_style.upper()),
        anchor_extend=args.anchor_extend
    ).write(args.output_dir, overwrite=args.overwrite, exclude_module_name=args.exclude_module_name)
