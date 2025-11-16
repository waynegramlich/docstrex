# docstrex: DOCument STRing EXtract -- Convert Python documentation strings to markdown.
The docstrex program takes a list of individual Python Files and/or directories
containing Python files, reads their associated documentation strings and
generates one `README.md` for each directory. The Python doc strings are
assumed to be written in markdown format so they can be readily concatonated
together.  If there is an `__init__.py` in a directory, its associated
documentation string is placed at the head of the generated `README.md` file.

The command line usage is:

     ```
     docstrex.py
       [--html] [--convert=MD_PROG] [--unit_tests] [PY_FILES_OR_DIRS...]
     ```

* [PY_FILE_OR_DIRS...]:
  Specifies zero, one or more Python files and/or directories that contain
  Python files.  All files are organized by directory and a single `README.md`
  file is written into  each directory.  If no files or directories are
  specified, the current working directory is scanned.

* If `--html` is present, each `README.md` file is converted to an associated
  `README.html` file.  If the `README.html` file is already present, the
  `--html` flag can be omitted.

* The default program to convert markdown into HTML is `markdown` program
  followed by `cmark` cmark program. If `--convert=MARKDOWN_PROG=...` is
  specified, is is used instead.

* if `--unit_tests` is set, the unit tests are run.  This flag is primarily
  used for to generate code coverage statistics.

## Table of Contents (alphabetical order):

* ?? Class: [Arguments](#):
  * 1.1 [process_further()](#docstrex----process-further): Further process the arguments of an Arguments object.
  * 1.2 [match_convert_flag()](#docstrex----match-convert-flag): Match the `--convert=...` flag.
  * 1.3 [match_output_flag()](#docstrex----match-output-flag): Match a 'output=...' flag.
  * 1.4 [match_html_flag()](#docstrex----match-html-flag): Match `--html` flag.
  * 1.5 [match_unit_tests_flag()](#docstrex----match-unit-tests-flag): Match --unit-tests flag.
  * 1.6 [match_file_or_directory()](#docstrex----match-file-or-directory): Process an argument if it is file or directory.
  * 1.7 [python_record()](#docstrex----python-record): Record the existance of Python file.
  * 1.8 [scan_directory()](#docstrex----scan-directory): Scan a directory for for Python files.
  * 1.9 [check_file_writable()](#docstrex----check-file-writable): Check if a file is writable.
  * 1.10 [run_unit_tests()](#docstrex----run-unit-tests): Run Arguments unit tests.
  * 1.11 [process()](#docstrex----process): Process the command line Arguments.
* ?? Class: [PyBase](#):
  * 2.1 [set_lines()](#docstrex----set-lines): Set the Lines field of a PyBase.
  * 2.2 [set_annotations()](#docstrex----set-annotations): Set the PyBase Anchor and Number attributes.
* ?? Class: [PyClass](#):
  * 3.1 [set_annotations()](#docstrex----set-annotations): Set the Markdown anchor.
  * 3.2 [summary_lines()](#docstrex----summary-lines): Return PyModule summary lines.
  * 3.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
* ?? Class: [PyFile](#):
  * 4.1 [process()](#docstrex----process): Process a PyFile.
* ?? Class: [PyFunction](#):
  * 5.1 [set_annotations()](#docstrex----set-annotations): Set the markdown annotations.
  * 5.2 [summary_lines()](#docstrex----summary-lines): Return PyModule table of contents summary lines.
  * 5.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
* ?? Class: [PyModule](#):
  * 6.1 [set_annotations()](#docstrex----set-annotations): Set the Markdown anchor.
  * 6.2 [summary_lines()](#docstrex----summary-lines): Return PyModule summary lines.
  * 6.3 [documentation_lines()](#docstrex----documentation-lines): Return the PyModule documentation lines.
  * 6.4 [generate()](#docstrex----generate): Generate the markdown and HTML files.
* ?? Class: [PyPackage](#):

## <a name=""></a>?? Class Arguments:

Command line arguments scanner.
Attributes:
* tracing (set): Set to " " to enable tracing and "" to disable.
* arguments (Sequence[str]):
  The command line arguments to process.
* convert_path: (Optional[Path]):
  The executable to to use to convert `README.md` into `README.html`.
* directories (Dict[Path, Set[Path]]):
  The directories contai1ning Python Files to be scanned.
* errors (List[str]):
  The list of errors collected during argument line parsing.
* html (bool):
  Enable `README.html` generation if enabled.
* markdown (Optional[path]): The markdown program to use.
* unit_tests: (bool):
  True to true if `--unit-tests` flag is present.
* tracing (str): If non-empty, tracing occurs.
  ...

Constructor:
* Arguments(tracing, command_line_arguments)

### <a name="docstrex----process-further"></a>1.1 `Arguments.`process_further():

Arguments.process_further(self, label: str, tracing: str = ''):

Further process the arguments of an Arguments object.

### <a name="docstrex----match-convert-flag"></a>1.2 `Arguments.`match_convert_flag():

Arguments.match_convert_flag(self, argument: str, tracing: str = '') -> bool:

Match the `--convert=...` flag.
Args:
* argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-output-flag"></a>1.3 `Arguments.`match_output_flag():

Arguments.match_output_flag(self, argument: str, tracing: str = '') -> bool:

Match a 'output=...' flag.
Args:
    argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-html-flag"></a>1.4 `Arguments.`match_html_flag():

Arguments.match_html_flag(self, argument, tracing: str = '') -> bool:

Match `--html` flag.
Args:
    argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-unit-tests-flag"></a>1.5 `Arguments.`match_unit_tests_flag():

Arguments.match_unit_tests_flag(self, argument, tracing: str = '') -> bool:

Match --unit-tests flag.
Args:
    argument (str): The argument to match against.

Returns:
    True if a match is found and False otherwise.

### <a name="docstrex----match-file-or-directory"></a>1.6 `Arguments.`match_file_or_directory():

Arguments.match_file_or_directory(self, argument: str, tracing: str = '') -> bool:

Process an argument if it is file or directory.
Arguments:
    file_name (str): The file name to check for writable.

Returns:
    True if writable and False otherwise.

### <a name="docstrex----python-record"></a>1.7 `Arguments.`python_record():

Arguments.python_record(self, python_path: pathlib.Path) -> None:

Record the existance of Python file.
Args:
* *python_path* (Path): The path to the Python file.

### <a name="docstrex----scan-directory"></a>1.8 `Arguments.`scan_directory():

Arguments.scan_directory(self, directory: pathlib.Path, tracing: str = '') -> bool:

Scan a directory for for Python files.
Args:
    directory (Path): The directory to scan.

Returns:
    (bool): True if a `.py` was encountered and `false` otherwise.

### <a name="docstrex----check-file-writable"></a>1.9 `Arguments.`check_file_writable():

Arguments.check_file_writable(file_name: str) -> bool:

Check if a file is writable.
Arguments:
    file_name (str): The file name to check for writable.

Returns:
    True if writable and False otherwise.

### <a name="docstrex----run-unit-tests"></a>1.10 `Arguments.`run_unit_tests():

Arguments.run_unit_tests(self, tracing: str = '') -> None:

Run Arguments unit tests.

### <a name="docstrex----process"></a>1.11 `Arguments.`process():

Arguments.process(self, tracing: str = '') -> int:

Process the command line Arguments.


## <a name=""></a>?? Class PyBase:

Base class of PyFunction, PyClass, PyModule, and PyPackage.
Attributes:
* *tracing* (str):
   If non-empty, code tracing occurs. (For debugging only.)
* *name* (str):
   The element name (i.e. function/class/module name.)
* *lines* (Tuple[str, ...]):
   The documentation string converted into lines with extraneous
   indentation removed. This attribute is set by the *set_lines*() method.
* *anchor* (str):
   The generated Markdown anchor for the documentation element.
   It is of the form "MODULE--CLASS--FUNCTION", where the
   module/class/function names have underscores converted to hyphens.
* *number* (str):
   The Table of contents number as a string.  '#" for classes and
   "#.#" for functions.

Constructor: Only sub-classes should use this.

### <a name="docstrex----set-lines"></a>2.1 `PyBase.`set_lines():

PyBase.set_lines(self, doc_string: Optional[str]) -> None:

Set the Lines field of a PyBase.
Arguments:
* *doc_string* (Optional[str]):
   A raw documentation string or None if no documentation string is
   present.

*doc_string* is split into lines.  Both the first line and all
subsequent empty lines are used to determine the actual doc string
indentation level.  The approproiate lines have their indentation
padding removed before being stored into PyBase.Lines attributes.

### <a name="docstrex----set-annotations"></a>2.2 `PyBase.`set_annotations():

PyBase.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the PyBase Anchor and Number attributes.
Arguments:
* *anchor_prefix* (str):
  The string to prepend to the document element name before setting
  the Anchor attribute.
* *number_prefix* (str):
  The string to prepend to the document element name before setting
  the Number attribute.

This method must be implemented by sub-classes.


## <a name=""></a>?? Class PyClass:

Represents a class method.
Inherited Attributes:
* *tracing (str): Used for trace debugging.
* *name* (str): The attribute name.
* *lines* (Tuple[str, ...]):
* *anchor* (str):
* *number* (str):

Attributes:
* *xclass* (Any): The underlying Python class object that is imported.
* *functions* (Tuple[PyFunction, ...]): The various functions associated
   with the Class.

Constructor:
* PyClass(tracing)

### <a name="docstrex----set-annotations"></a>3.1 `PyClass.`set_annotations():

PyClass.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the Markdown anchor.

### <a name="docstrex----summary-lines"></a>3.2 `PyClass.`summary_lines():

PyClass.summary_lines(self, indent: str) -> Tuple[str, ...]:

Return PyModule summary lines.

### <a name="docstrex----documentation-lines"></a>3.3 `PyClass.`documentation_lines():

PyClass.documentation_lines(self, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.


## <a name=""></a>?? Class PyFile:

A class that is one-to-one with a Python file.
Attributes:
* *python_path* (Path):
  The path to the Python source.
* *convert_path* (Optional[Path]):
  The program path that coverts a .md file into a .html file (or None).
  Defaults to None, if no converter is present.
* *markdown_path* (Path):
  The path to the generated markdown (.md) file.
* *html_path* (Path):
  The path to the generated HTML (.html) file.
* *detects_main* (bool):
  True if either `if __name__ == "__main__:"` or
  `if __name__ == '__main__:` is present in file.
  (Default is False.)
* has_main: (bool):
  True if `def main(` is present in file.  (Default is False.)

Constructor:
* PyFile(tracing, python_path, markdown_path, convert_path, html_path)

### <a name="docstrex----process"></a>4.1 `PyFile.`process():

PyFile.process(self, modules: 'List[PyModule]', markdown_path: pathlib.Path, convert_path: Optional[pathlib.Path], html_path: pathlib.Path, errors: List[str], tracing: str = '') -> None:

Process a PyFile.
Arguments:
* modules (List[PyModule]): A list to collect all PyModules onto.
* markdown_path (Path}: The path for the `README.md` file.
* convert_path (Optional(Path)):
  The path to the program to convert .md into .html.
* html_path (Path): The path for the `README.html` file.
* errors (List[str]): A list to collect any generated errors on.

Process the PyFile (*self*) and append the generated PyModule's to
*modules*.  Any error message lines are appended to *error*s.


## <a name=""></a>?? Class PyFunction:

Represents a function or method.
Inherited Attributes:
* *tracing* (str)
* *name* (str)
* *lines* (Tuple[str, ...])
* *anchor* (str)
* *number* (str)

Attributes:
*  *function* (Callable): The actual function/method object.

Constructor:
* PyFunction(tracing, name, lines, anchor, number, function)

### <a name="docstrex----set-annotations"></a>5.1 `PyFunction.`set_annotations():

PyFunction.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the markdown annotations.
(see [ModeDoc.set_annoations](#Doc-PyBase-set_annotations)

### <a name="docstrex----summary-lines"></a>5.2 `PyFunction.`summary_lines():

PyFunction.summary_lines(self, class_name: str, indent: str) -> Tuple[str, ...]:

Return PyModule table of contents summary lines.
Arguments:
* *class_name*: The class name the function is a member of.
* *indent* (int) The prefix spaces to make the markdown work.

Returns:
* (Tuple[str, ...]): The resulting summary lines.

### <a name="docstrex----documentation-lines"></a>5.3 `PyFunction.`documentation_lines():

PyFunction.documentation_lines(self, class_name: str, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.
Arguments:
* *class_Name* (str): The class name to use for methods.
* *prefix* (str): The prefix to use to make the markdown work.

Returns:
* (Tuple[str, ...]): The resulting documentations lines


## <a name=""></a>?? Class PyModule:

Represents a Python module (i.e. file).
The generated Markdown anchor for the documentation element.
It is of the form "MODULE--CLASS--FUNCTION", where the
module/class/function names have underscores converted into hyphens.

Inherited Attributes:
* *tracing* (str):
* *name* (str):
* *lines* (Tuple[str, ...]):
* *anchor* (str):
* *number* (str):

New Attributes:
* *module* (Any): The Python module object.
* *classes* (Tuple[PyClass, ...]):
#   The classes defined by the Python module object.

Constructor:
* PyModule(tracing, module, classes)

### <a name="docstrex----set-annotations"></a>6.1 `PyModule.`set_annotations():

PyModule.set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:

Set the Markdown anchor.

### <a name="docstrex----summary-lines"></a>6.2 `PyModule.`summary_lines():

PyModule.summary_lines(self) -> Tuple[str, ...]:

Return PyModule summary lines.

### <a name="docstrex----documentation-lines"></a>6.3 `PyModule.`documentation_lines():

PyModule.documentation_lines(self, prefix: str) -> Tuple[str, ...]:

Return the PyModule documentation lines.

### <a name="docstrex----generate"></a>6.4 `PyModule.`generate():

PyModule.generate(self, markdown_path: pathlib.Path, convert_path: Optional[pathlib.Path], html_path: pathlib.Path, tracing: str = '') -> None:

Generate the markdown and HTML files.


## <a name=""></a>?? Class PyPackage:

Represents a Python package `__init.py__` file.
Inherited Attributes:
* *tracing* (str)
* *name* (str)
* *lines* (Tuple[str, ...])
* *anchor* (str)
* *number* (str)

Attributes:
* *Class* (Any): The underlying Python class object that is imported.
* *Functions* (Tuple[PyFunction, ...]): The functions of the Class.

Constructor:
* PyPackage()



