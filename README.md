# docstrex: docxtrex: DOCument STRing EXtract -- Convert doc strings to markdown.
This program takes a list of individual Python Files and/or directories containing Python files,
reads the associated documentation strings and generates a single Markdown file.

The simple command line usage is:
     ```
     docstrex.py [--outfile=OUT_FILE] [--markdown=MARKDOWN_PROG] [--unit_tests] [PY_FILE_OR_DIR...]
     ```
If `--outfile=FILE` is not specified, `README.md` is generated in the current working directory.
If `--markdown=MARKDOWN_PROG` is specified, MARKDOWN_PROG is used to convert OUTFILE to an
HTML (`.html`) file.  The remaining arguments are one or more Python (`.py`) files or directories
that contain python files (`.py`)  If no files or directories are specified, the current working
directory is scanned for Python files.  (If `--unit_tests]` is specified, the unit tests are
are run.)

When an `__init__.py` is present in a scanned directory, it indicates that the directory should
be treated as a Python package.  As such, the first documentation string in the `__init__.py` file
is shown first in the documentation for the Python package.

## Table of Contents (alphabetical order):

* 1 Class: [Arguments](#docstrex--arguments):
  * 1.1 [scan_directory()](#docstrex----scan-directory): Scan directory for Python files.
  * 1.2 [unit_tests()](#docstrex----unit-tests): Run unit tests on Arguments.
* 2 Class: [Arguments2](#docstrex--arguments2):
  * 2.1 [process_arguments()](#docstrex----process-arguments): Process the arguments for an Arguments2 object.
  * 2.2 [match_markdown_flag()](#docstrex----match-markdown-flag): Match the `markdown=...` flag.
  * 2.3 [match_output_flag()](#docstrex----match-output-flag): Match a 'output=...' flag.
  * 2.4 [match_unit_tests_flag()](#docstrex----match-unit-tests-flag): Match --unit-tests flag.
  * 2.5 [match_file_or_directory()](#docstrex----match-file-or-directory): Process an argument if it is file or directory.
  * 2.6 [scan_directory()](#docstrex----scan-directory): Scan a directory for Python files.
  * 2.7 [check_file_writable()](#docstrex----check-file-writable): Check if a file is writable.
  * 2.8 [run_unit_tests()](#docstrex----run-unit-tests): Run Arguments2 unit tests.
* 3 Class: [PyBase](#docstrex--pybase):
  * 3.1 [set_lines()](#docstrex----set-lines): Set the Lines field of a PyBase.
  * 3.2 [set_annotations()](#docstrex----set-annotations): Set the PyBase Anchor and Number attributes.
* 4 Class: [PyClass](#docstrex--pyclass):
  * 4.1 [set_annotations()](#docstrex----set-annotations): Set the Markdown anchor.
  * 4.2 [summary_lines()](#docstrex----summary-lines): Return PyModule summary lines.
  * 4.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
* 5 Class: [PyFile](#docstrex--pyfile):
  * 5.1 [process()](#docstrex----process): Process a PyFile.
* 6 Class: [PyFunction](#docstrex--pyfunction):
  * 6.1 [set_annotations()](#docstrex----set-annotations): Set the markdown annotations.
  * 6.2 [summary_lines()](#docstrex----summary-lines): Return PyModule table of contents summary lines.
  * 6.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
* 7 Class: [PyModule](#docstrex--pymodule):
  * 7.1 [set_annotations()](#docstrex----set-annotations): Set the Markdown anchor.
  * 7.2 [summary_lines()](#docstrex----summary-lines): Return PyModule summary lines.
  * 7.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
  * 7.4 [generate()](#docstrex----generate): Generate the markdown and HTML files.
* 8 Class: [PyPackage](#docstrex--pypackage):

## <a name="docstrex--arguments"></a>1 Class Arguments:

A class for processing command line arguments.
The reason for the *Arguments* class to is make it easier to do unit tests on the command
line processing code.

Attributes:
* *arguments*:
  The original command line arguments excluding the initial program name (i.e. `sys.argv[1:]`).
* *python_files* (List[PyFile, ...]):
  The associated PyFile objects for each Python (.py) file to be processed.
* *errors* (Tuple[str, ...]):
  A list of error strings that get generated.
* unit_test* (bool):
* *markdown_program* (Optional[Path]):
* *sorted_python_files* (Tuple[PyFile, ...]):
  The PyFile's sorted by their Path name.

Constructor:
* Arguments(arguments)  # See Arguments.__post_init__() for more details

### <a name="docstrex----scan-directory"></a>1.1 `Arguments.`scan_directory():

Arguments.scan_directory(self, directory_path: pathlib.Path, docs_directory: pathlib.Path, tracing: str = '') -> None:

Scan directory for Python files.
Arguments:
* *directory_path* (Path):
   The directory to scan for Python files.  If no Python files are found, generate an error.
* *docs_directory* (Path):
   The directory path to write .md and .html into.

Returns:
* Nothing

### <a name="docstrex----unit-tests"></a>1.2 `Arguments.`unit_tests():

Arguments.unit_tests(self, tracing: str = ''):

Run unit tests on Arguments.


## <a name="docstrex--arguments2"></a>2 Class Arguments2:

The new and improved arguments scanner.
Attributes:
* arguments (Sequence[str]):
  The command line arguments to process.
* errors (List[str]):
  The list of errors collected during argument line parsing.
* markdown: (Optional[Path]):
  The executable to to use to convert markdown into HTML.
* output_path: (Optional[Path]):
  The file to write the output to.
* package_paths: Tuple[Path, ...]:
  The directories that contain Python packages (i.e. an `__init__.py` file.)
* python_paths: Tuple[Path, ...]:
  The paths to the Python files to scan.
* unit_tests: (bool):
  True to true if `--unit-tests` flag is present.
* tracing: (str):
  ...

Constructor:
* Arguments2(arguments)

### <a name="docstrex----process-arguments"></a>2.1 `Arguments2.`process_arguments():

Arguments2.process_arguments(self, label: str, tracing: str = ''):

Process the arguments for an Arguments2 object.

### <a name="docstrex----match-markdown-flag"></a>2.2 `Arguments2.`match_markdown_flag():

Arguments2.match_markdown_flag(self, argument: str, tracing: str = '') -> bool:

Match the `markdown=...` flag.
Args:
* argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-output-flag"></a>2.3 `Arguments2.`match_output_flag():

Arguments2.match_output_flag(self, argument: str, tracing: str = '') -> bool:

Match a 'output=...' flag.
Args:
    argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-unit-tests-flag"></a>2.4 `Arguments2.`match_unit_tests_flag():

Arguments2.match_unit_tests_flag(self, argument, tracing: str = '') -> bool:

Match --unit-tests flag.
Args:
    argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-file-or-directory"></a>2.5 `Arguments2.`match_file_or_directory():

Arguments2.match_file_or_directory(self, argument: str, tracing: str = '') -> bool:

Process an argument if it is file or directory.
Arguments:
    file_name (str): The file name to check for writable.

Returns:
    True if writable and False otherwise.

### <a name="docstrex----scan-directory"></a>2.6 `Arguments2.`scan_directory():

Arguments2.scan_directory(self, directory: pathlib.Path, errors: List[str], tracing: str = '') -> bool:

Scan a directory for Python files.
Args:
* directory (Path): The directory of Pythongfiles to process.
* errors (List[str]): An error list to append errors to.

Returns:
* (bool): True for sucess and False otherwise:

### <a name="docstrex----check-file-writable"></a>2.7 `Arguments2.`check_file_writable():

Arguments2.check_file_writable(file_name: str) -> bool:

Check if a file is writable.
Arguments:
    file_name (str): The file name to check for writable.

Returns:
    True if writable and False otherwise.

### <a name="docstrex----run-unit-tests"></a>2.8 `Arguments2.`run_unit_tests():

Arguments2.run_unit_tests(self, tracing: str = '') -> None:

Run Arguments2 unit tests.


## <a name="docstrex--pybase"></a>3 Class PyBase:

Base class for the PyFunction, PyClass, PyModule, and PyPackage classes.
Attributes:
* *Name* (str):
   The element name (i.e. function/class/module name.)
* *Lines* (Tuple[str, ...]):
   The documentation string converted into lines with extraneous indentation removed.
   This attribute is set by the *set_lines*() method.
* *Anchor* (str):
   The generated Markdown anchor for the documentation element.
   It is of the form "MODULE--CLASS--FUNCTION", where the module/class/function names
   have underscores converted to hyphens.
* *Number* (str):
   The Table of contents number as a string.  '#" for classes and "#.#" for functions.

### <a name="docstrex----set-lines"></a>3.1 `PyBase.`set_lines():

PyBase.set_lines(self, doc_string: Optional[str]) -> None:

Set the Lines field of a PyBase.
Arguments:
* *doc_string* (Optional[str]):
   A raw documentation string or None if no documentation string is present.

*doc_string* is split into lines.  Both the first line and all subsequent empty lines
are used to determine the actual doc string indentation level.  The approproiate
lines have their indentation padding removed before being stored into PyBase.Lines
attributes.

### <a name="docstrex----set-annotations"></a>3.2 `PyBase.`set_annotations():

PyBase.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the PyBase Anchor and Number attributes.
Arguments:
* *anchor_prefix* (str):
  The string to prepend to the document element name before setting the Anchor attribute.
* *number_prefix* (str):
  The string to prepend to the document element name before setting the Number attribute.

This method must be implemented by sub-classes.


## <a name="docstrex--pyclass"></a>4 Class PyClass:

Represents a class method.
Inherited Attributes:
* *Name* (str): The attribute name.
* *Lines* ( , *Anchor*, *Number* from PyBase.

Attributes:
* *Class* (Any): The underlying Python class object that is imported.
* *Functions* (Tuple[PyFunction, ...]): The various functions associated with the Class.

Constructor:
* PyClass()

### <a name="docstrex----set-annotations"></a>4.1 `PyClass.`set_annotations():

PyClass.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the Markdown anchor.

### <a name="docstrex----summary-lines"></a>4.2 `PyClass.`summary_lines():

PyClass.summary_lines(self, indent: str) -> Tuple[str, ...]:

Return PyModule summary lines.

### <a name="docstrex----documentation-lines"></a>4.3 `PyClass.`documentation_lines():

PyClass.documentation_lines(self, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.


## <a name="docstrex--pyfile"></a>5 Class PyFile:

A class that is one-to-one with a Python file.
Attributes:
* *py_path* (Path):
  The path to the Python source.
* *md_path* (Path):
  The path to the generated markdown (.md) file.
* *html_path* (Path):
   The path to the generated HTML (.html) file.
* *markdown_program* (Optional[str]):
  The path to the program that coverts a .md file into a .html file.
  Defaults to None, if no converter is present.
* *detects_main* (bool):
  True if either `if __name__ == "__main__:"` or `if __name__ == '__main__:` is present in file.
  (Default is False.)
* has_main: (bool):
  True if `def main(` is present in file.  (Default is False.)

Constructor:
* PyFile(py_path, md_path, html_path, markdown_convert)

### <a name="docstrex----process"></a>5.1 `PyFile.`process():

PyFile.process(self, modules: 'List[PyModule]', errors: List[str], tracing: str = '') -> None:

Process a PyFile.
Arguments:
* modules (List[PyModule]): A list to collect all PyModules onto.
* errors (List[str]): A list to collect any generated errors on.

Process the PyFile (*self*) and append the generated PyModule to *modulues*.
Any error message lines are append to *error*s.


## <a name="docstrex--pyfunction"></a>6 Class PyFunction:

Represents a function or method.
Inherited Attributes:
* *Name* (str)
* *Lines* (Tuple[str, ...])
* *Anchor* (str)
* *Number* (str)

Attributes:
*  *Function* (Callable): The actual function/method object.

Constructor:
* PyFunction(Name, Lines, Anchor, Number, Function)

### <a name="docstrex----set-annotations"></a>6.1 `PyFunction.`set_annotations():

PyFunction.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the markdown annotations.
(see [ModeDoc.set_annoations](#Doc-PyBase-set_annotations)

### <a name="docstrex----summary-lines"></a>6.2 `PyFunction.`summary_lines():

PyFunction.summary_lines(self, class_name: str, indent: str) -> Tuple[str, ...]:

Return PyModule table of contents summary lines.
Arguments:
* *class_name*: The class name the function is a member of.
* *indent* (int) The prefix spaces to make the markdown work.

Returns:
* (Tuple[str, ...]): The resulting summary lines.

### <a name="docstrex----documentation-lines"></a>6.3 `PyFunction.`documentation_lines():

PyFunction.documentation_lines(self, class_name: str, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.
Arguments:
* *class_Name* (str): The class name to use for methods.
* *prefix* (str): The prefix to use to make the markdown work.

Returns:
* (Tuple[str, ...]): The resulting documentations lines


## <a name="docstrex--pymodule"></a>7 Class PyModule:

Represents a module.

### <a name="docstrex----set-annotations"></a>7.1 `PyModule.`set_annotations():

PyModule.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the Markdown anchor.

### <a name="docstrex----summary-lines"></a>7.2 `PyModule.`summary_lines():

PyModule.summary_lines(self) -> Tuple[str, ...]:

Return PyModule summary lines.

### <a name="docstrex----documentation-lines"></a>7.3 `PyModule.`documentation_lines():

PyModule.documentation_lines(self, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.

### <a name="docstrex----generate"></a>7.4 `PyModule.`generate():

PyModule.generate(self, markdown_path: pathlib.Path, markdown_program: str, tracing: str = '') -> None:

Generate the markdown and HTML files.


## <a name="docstrex--pypackage"></a>8 Class PyPackage:

Represents a Python package `__init.py__` file.
Inherited Attributes:
* *Name* (str): The package name (i.e name of directory containing the `__init__.py` file.)
* *Lines* (Tuple[str, ...) , *Anchor*, *Number* from PyBase.

Attributes:
* *Class* (Any): The underlying Python class object that is imported.
* *Functions* (Tuple[PyFunction, ...]): The various functions associated with the Class.

Constructor:
* PyPackage()



