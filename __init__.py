"""docstrex: python DOCument STRing EXtract to markdown format.

<!---------------------------------------- 100 characters ----------------------------------------->

## Table of Contents:

* [Introduction](#introduction)
* [Installation](#installation)
* [Overview](#overview)
* [Miscellaneous](#miscellaneous)
* [License](#license)

## Introduction

`docstrex.py` stands for "python DOCument STRing EXTract to markdown format.  It is a program
that scans the document strings in Python files and generates associated markdown (`.md`) files.
In addition, if can also convert the markdown files into HTML (`.html`) files so they can be
previewed in a web browser.  The comments in the Python document strings are written in pretty
generic [markdown](https://www.markdownguide.org/) format.  Thus, `docstrex` program mostly just
copies the Python document strings out of the Python file (`.py`) and inserts them into a markdown
file (`.md`) with very little additional markdown added to improve readability.  Some popular
software repository sites (e.g. [github](github.com) automatically convert HTML files into
markdown so they easily browsed in a web browser.

There are other systems out there (e.g. [Sphinx](https://www.sphinx-doc.org/)), that do similar
tasks, but they tend to be harder to install, setup and use.

## Installation

The easiest way to install this program is directly from GitHub at
[docstrex](https://github.com/waynegramlich/docstrex).
If you have [git](https://git-scm.com/) installed on your system,
you an download the code via:

     ```
     cd .../git_downloads_directory  # A directory used to download git projects into
     git clone https://github.com/waynegramlich/docstrex.git
     ```

The program is executed by

     ```
     cd .../directory_containing_you_python_code
     python3 .../git_downloads_directory/docstrx/docstrex.py  # Optional flags can be specified.
     ```
This will scan the current directory for `.py` files, and create a `docs/` directory that
contains the generated markdown (`.md`) and HTML (`.html`) files

On a system that is compatible with Linux, execution can be simplified to:

     ```
     cd .../directory_containing_python_code
     .../git_downloads_directory/pyds2md.py
     ```

There are additional command line flags that are described in a section immediately below:

## Command Line Flags

The command line summary is:

     ```
     pyds2md [PY_FILE...] [PY_DIR...] [--docs=DIR] [--markdown=PROG] [--unit_test]
     ```

where:

* `[PY_FILE...]`; is zero, one, or more files that end with a `.py` suffix.
* `[PY_DIR...]`; is a directory containing at least one or more `.py` files.
* `[--docs=DIR]`:
   specifies a documentation directory in which to store generated `.md` and `.html` files into.
   If not specified, the `docs` directory in the current working directory is used.
* `[--markdown=PROG]`: specifies the HTML to markdown converter program to use.
   This defaults to the `cmark` if it available.  If no markdown converter is available,
   no `.md`. to `.html` file generation occurs.
* `[--unit-test]`: specifies that the unit tests are to be run.
   This is usually used by the py2dsmd developers to perform code coverage tests.

The flags are processed left to right.  The `-directory=` and `--markdown=` can be specified
more than once.

This simplest execution is with no command line options:

    ```
    pyds2md
    ```

which scans the current working directory and stores the generated files into `docs` directory.

A more complex command line is:

    ```
    pyds2m --markdown=PROG1 --docs=DOCS1/docs --markdown=PROG2 --docs=DOCS2/docs
    ```

which:

1. Scans `DIR1` storing generated documents into `DOCS/docs`
   using `PROG1` to convert `.md` files into `.html` files.

2. Scans `DIR2` storing generated documents into `DOCS2/docs`
   using `PROG2` to convert `.md` files into `.html` files.


## Documentation Strategy.

### Type Hints

Python type hints are fully supported in Python3 and should be used to specify the class
attribute types and function/method argument and return types.
See (PEP 484 - Type Hints)(https://peps.python.org/pep-0484/)

Along similar lines, [PEP 575 - Data Classes](https://peps.python.org/pep-0557/) is a
useful way of using type hints to document Python classes using type hints.

### First Doc String

The first doc string usually starts on the first or second line of the Python file.
For Unix-like operating system systems (e.g. Linux), the first line frequently starts with 
`#!/usr/bin/python3` with the execute permissions turned on.  The first line of the
doc string is usually a one line abbreviation of what the program does.  The example
below has the first few lines from `pyds2md.py`.

     ```
     '''Doc: Convert Python doc strings to Markdown files.

     The Doc program reads Python files and generates Markdown files from embedded doc strings.
     These files can be converted into HTML files via a Markdown program like `cmark`.

          Usage:
            python3 Doc.py [--docs=DOCS_DIR] [--markdown=CONVERTER] [FILES_NAMES_OR_DIRS...]
      ...
      '''
      ```
### Class Doc Strings

Each class should have a top level documentation string.
You are free to put an markdown in to the top-level documenation string.
The following is a reasonable format to use:

     ```
     '''ClassName: One line description of class.
    
     One or more paragraphs that describe the class in greater detail.

     Attributes:
     * *attribute1 (type):
       A description of the first attribute using full sentences.

     * ...

     * *attributeN* (type):
       A description of the last attribute using full sentences.

     Constructor:
     * ClassName(attribute1, ..., attributeN)
     '''
     ```

The class attributes are described using itemized list.  This includes attributes
that implemented using the `@property` decorator for setter and getter methods.

If the class is a subclass of another class, that should be mentioned in the document string.  Any
inherited attributes should be listed as `Inherited Attributes:` before the `Attributes` section.
Also, for Python dataclasses, if there is a default attribute value it should be mentioned
in the attribute description.

The reason for the `Constructor:` is because sometimes it can be challenging to figure out
how to construct a class that is sub-class one or more parent classes.
The `Constructor:` makes it so people do not have engage in a deep investigation in the code
base just to figure out how to instantiate the class.

### Function/Method Doc Strings

A typical function/method documentation string looks like:

     ```One line function/method description ending in a period.
     '''
     Arguments:
     * *arg1* (type1):
       Description of the first argument.

     ...

     * *argN* (typeN):
       Description of the last argument.

     Returns:
     * (RetType1): Description of the first return type.

     ...

     * (RetTypeN): Description of the last return type.

     Raises:
     * ExceptionClass1:
       If the exception class needs any further description, it is placed here.
       For standard Python [Built-inExceptions](https://docs.python.org/3/library/exceptions.html),
       it is probably sufficient to use list the exception class name (e.g. `RuntimeError`.)

     Further description of the function method goes here, if needed.
     '''
     ```

Each function/method has the entire function/method type signature including type hints
copied into the generated documentation.

## Miscellaneous

1. The unit test suite and associated code coverage is done using:

     ```
     make cover
     ```

2. More miscellany goes here...

## License

Thus, this code is released under the [MIT license](https://mit-license.org/).  By the way,
the original author of this code (Wayne Gramlich) has a long history of using the MIT license
(see [The Origin of the "MIT License"](https://www.mit.edu/~Saltzer/publications/MITLicense.pdf) ).
The original author is also open to using other licenses.

"""

