# Sophia-doc

**A python package to automatically generate API documents for Python modules.**

## Introduction

Sophia is a python package to automatically generate API documents for Python modules.

It's a lot like sphinx, but it only focuses on generating markdown documentation.

It does not support PEP 224 attribute docstring, because the PEP was rejected, and have to use ast module to support it, which brings additional complexity to this project.

## Install

```sh
pip install sophia-doc
```

## Quickstart

```sh
sophia_doc "sophia_doc" -o ./doc
```

## Usage

Command line:

```txt
usage: sophia_doc [-h] [-o OUTPUT_DIR] [--docstring-style DOCSTRING_STYLE] [--anchor-extend | --no-anchor-extend] [--overwrite | --no-overwrite]
                   [--exclude-module-name | --no-exclude-module-name]
                   module

Sophia_doc is a python package to automatically generate API documents for Python modules

positional arguments:
  module                Python module names.

options:
  -h, --help            show this help message and exit
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        The directory to write document. (default: doc)
  --docstring-style DOCSTRING_STYLE
                        Docstring style the python module used. (default: auto)
  --anchor-extend, --no-anchor-extend
                        Add anchor to markdown title. (default: False)
  --overwrite, --no-overwrite
                        Overwrite any file in output directory. (default: False)
  --exclude-module-name, --no-exclude-module-name
                        Write file to path which exclude module name. (default: False)
```

## License

MIT © st1020
