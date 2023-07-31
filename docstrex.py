#!/usr/bin/env python3
"""docxtrex: DOCument STRing EXtract -- Convert doc strings to markdown.

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

"""

# <--------------------------------------- 100 characters ---------------------------------------> #


from dataclasses import dataclass, field
import importlib
import inspect
import os
from pathlib import Path
import shutil  # Used for shutil.which()
import subprocess
import sys
import tempfile  # Used for unit tests.
from typing import Any, Callable, cast, Dict, IO, List, Optional, Sequence, Tuple


# PyBase:
@dataclass
class PyBase(object):
    """PyBase: Base class for the PyFunction, PyClass, PyModule, and PyPackage classes.

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

    """

    Name: str = field(init=False, default="")
    Lines: Tuple[str, ...] = field(init=False, repr=False, default=())
    Anchor: str = field(init=False, repr=False, default="")
    Number: str = field(init=False, repr=False, default="??")

    # PyBase.set_lines():
    def set_lines(self, doc_string: Optional[str]) -> None:
        """Set the Lines field of a PyBase.

        Arguments:
        * *doc_string* (Optional[str]):
           A raw documentation string or None if no documentation string is present.

        *doc_string* is split into lines.  Both the first line and all subsequent empty lines
        are used to determine the actual doc string indentation level.  The approproiate
        lines have their indentation padding removed before being stored into PyBase.Lines
        attributes.

        """
        self.Lines = ("NO DOC STRING!",)
        if isinstance(doc_string, str):
            line: str
            lines: List[str] = [line.rstrip() for line in doc_string.split("\n")]

            # Compute the *common_indent* in spaces ignoring empty lines:
            big: int = 123456789
            common_indent: int = big
            # The first line of a doc string has no indentation padding, but all other lines do.
            for line in lines[1:]:
                indent: int = len(line) - len(line.lstrip())
                if line:  # Skip empty lines:
                    common_indent = min(common_indent, indent)
            if common_indent == big:
                common_indent = 0

            # Convert "NAME: Summary line." => "Summary_line.":
            first_line: str = lines[0]
            pattern: str = f"{self.Name}: "
            if first_line.startswith(pattern):
                lines[0] = first_line[len(pattern):]

            # Strip the common indentation off of each *line*:
            index: int
            for index, line in enumerate(lines):
                if index > 0 and len(line) >= common_indent:
                    lines[index] = line[common_indent:]

            # Strip off blank lines from the end:
            while lines and lines[-1] == "":
                lines.pop()

            # Strip off blank lines between summary line and body:
            while len(lines) >= 2 and lines[1] == "":
                del(lines[1])

            self.Lines = tuple(lines)

    # PyBase.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the PyBase Anchor and Number attributes.

        Arguments:
        * *anchor_prefix* (str):
          The string to prepend to the document element name before setting the Anchor attribute.
        * *number_prefix* (str):
          The string to prepend to the document element name before setting the Number attribute.

        This method must be implemented by sub-classes.

        """
        raise NotImplementedError(f"{self}.set_annotations() is not implemented.")


# PyFunction:
@dataclass
class PyFunction(PyBase):
    """PyFunction: Represents a function or method.

    Inherited Attributes:
    * *Name* (str)
    * *Lines* (Tuple[str, ...])
    * *Anchor* (str)
    * *Number* (str)

    Attributes:
    *  *Function* (Callable): The actual function/method object.

    Constructor:
    * PyFunction(Name, Lines, Anchor, Number, Function)

    """

    Function: Callable

    # PyFunction.__post_init__():
    def __post_init__(self) -> None:
        """Post process a PyFunction."""
        function: Callable = self.Function
        if hasattr(function, "__name__"):
            self.Name = getattr(function, "__name__")
        if hasattr(function, "__doc__"):
            self.set_lines(getattr(function, "__doc__"))

    # PyFunction.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the markdown annotations.

        (see [ModeDoc.set_annoations](#Doc-PyBase-set_annotations)

        """
        self.Anchor = anchor_prefix + self.Name.lower().replace("_", "-")
        self.Number = number_prefix

    # PyFunction.summary_lines():
    def summary_lines(self, class_name: str, indent: str) -> Tuple[str, ...]:
        """Return PyModule table of contents summary lines.

        Arguments:
        * *class_name*: The class name the function is a member of.
        * *indent* (int) The prefix spaces to make the markdown work.

        Returns:
        * (Tuple[str, ...]): The resulting summary lines.

        """
        assert self.Lines, f"{class_name=}"
        return (f"{indent}* {self.Number} [{self.Name}()]"
                f"(#{self.Anchor}): {self.Lines[0]}",)

    # PyFunction.documentation_lines():
    def documentation_lines(self, class_name: str, prefix: str) -> Tuple[str, ...]:
        """Return the PyModule documentation lines.

        Arguments:
        * *class_Name* (str): The class name to use for methods.
        * *prefix* (str): The prefix to use to make the markdown work.

        Returns:
        * (Tuple[str, ...]): The resulting documentations lines

        """
        lines: Tuple[str, ...] = self.Lines
        signature: inspect.Signature = inspect.Signature.from_callable(self.Function)
        doc_lines: Tuple[str, ...] = (
            (f"{prefix} <a name=\"{self.Anchor}\"></a>{self.Number} "
             f"`{class_name}.`{self.Name}():"),
            "",
            f"{class_name}.{self.Name}{signature}:",
            ""
        ) + lines + ("",)
        return doc_lines


# PyClass:
@dataclass
class PyClass(PyBase):
    """PyClass: Represents a class method.

    Inherited Attributes:
    * *Name* (str): The attribute name.
    * *Lines* ( , *Anchor*, *Number* from PyBase.

    Attributes:
    * *Class* (Any): The underlying Python class object that is imported.
    * *Functions* (Tuple[PyFunction, ...]): The various functions associated with the Class.

    Constructor:
    * PyClass()

    """

    Class: Any = field(repr=False)
    Functions: Tuple[PyFunction, ...] = field(init=False, default=())

    # PyClass.__post_init__():
    def __post_init__(self) -> None:
        """Post process PyClass."""
        # Set Name and Lines attributes:
        if hasattr(self.Class, "__name__"):
            self.Name = cast(str, getattr(self.Class, "__name__"))
        if hasattr(self.Class, "__doc__"):
            self.set_lines(cast(str, getattr(self.Class, "__doc__")))

        # Set the Functions attribute:
        py_functions: List[PyFunction] = []
        attribute_name: str
        attribute: Any
        for attribute_name, attribute in self.Class.__dict__.items():
            if not attribute_name.startswith("_") and callable(attribute):
                py_functions.append(PyFunction(attribute))
        self.Functions = tuple(py_functions)

    # PyClass.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the Markdown anchor."""
        anchor: str = anchor_prefix + self.Name.lower().replace("_", "-")
        self.Anchor = anchor
        self.Number = number_prefix

        next_anchor_prefix: str = anchor_prefix + "--"
        py_function: PyFunction
        for index, py_function in enumerate(self.Functions):
            py_function.set_annotations(next_anchor_prefix, f"{number_prefix}.{index + 1}")

    # PyClass.summary_lines():
    def summary_lines(self, indent: str) -> Tuple[str, ...]:
        """Return PyModule summary lines."""
        lines: List[str] = [
            f"{indent}* {self.Number} Class: [{self.Name}](#{self.Anchor}):"]
        next_indent: str = indent + "  "
        py_function: PyFunction
        for py_function in self.Functions:
            lines.extend(py_function.summary_lines(self.Name, next_indent))
        return tuple(lines)

    # PyClass.documentation_lines():
    def documentation_lines(self, prefix: str) -> Tuple[str, ...]:
        """Return the PyModule documentation lines."""
        lines: Tuple[str, ...] = self.Lines
        doc_lines: List[str] = [
            f"{prefix} <a name=\"{self.Anchor}\"></a>{self.Number} Class {self.Name}:",
            "",
        ]
        doc_lines.extend(lines)
        doc_lines.append("")
        next_prefix: str = prefix + "#"
        function: PyFunction
        for function in self.Functions:
            doc_lines.extend(function.documentation_lines(self.Name, next_prefix))
        doc_lines.append("")
        return tuple(doc_lines)


# PyModule:
@dataclass
class PyModule(PyBase):
    """PyModule: Represents a module."""

    Module: Any = field(repr=False)
    Classes: Tuple[PyClass, ...] = field(init=False, default=())

    # PyModule.__post_init__():
    def __post_init__(self) -> None:
        """Recursively extract information from an object."""
        module: Any = self.Module

        # Get initial *module_name*:
        module_name: str = ""
        if hasattr(module, "__name__"):
            module_name = getattr(module, "__name__")
        is_package: bool = module_name == "__init__"

        tracing: str = "" if is_package else ""  # Change first string to enable package tracing.
        if tracing:
            print(f"{tracing}Processing {module_name} {is_package=}")
        if hasattr(module, "__doc__"):
            doc_string = getattr(module, "__doc__")
            if tracing:
                print(f"{tracing}{doc_string=}")
            self.set_lines(doc_string)
            if is_package:
                first_line: str = self.Lines[0]
                colon_index: int = first_line.find(":")
                if colon_index >= 0:
                    module_name = first_line[:colon_index]
                    first_line = first_line[colon_index + 2:]  # Skip over "...: "
                    self.Lines = (first_line,) + self.Lines[1:]

        # The Python import statement can import class to the module namespace.
        # We are only interested in classes that are defined in *module*:
        py_classes: List[PyClass] = []
        class_type: type = type(PyBase)  # Any class name to get the associated class type.
        assert isinstance(class_type, type)
        attribute_name: str
        # print(f"{module=} {type(module)=}")
        for attribute_name in dir(module):
            if not attribute_name.startswith("_"):
                attribute: Any = getattr(module, attribute_name)
                if hasattr(attribute, "__module__"):
                    defining_module: Any = getattr(attribute, "__module__")
                    # print(f"{attribute_name=} {attribute=} {defining_module}")
                    if isinstance(attribute, class_type) and str(defining_module) == module_name:
                        py_classes.append(PyClass(attribute))
                        # print(f">>>>>>>>>>Defined class: {attribute_name}")
        self.Name = module_name
        self.Classes = tuple(py_classes)

    # PyModule.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the Markdown anchor."""
        anchor: str = anchor_prefix + self.Name.lower().replace("_", "-")
        self.Anchor = anchor

        next_anchor_prefix: str = anchor + "--"
        py_class: PyClass
        index: int
        for index, py_class in enumerate(self.Classes):
            py_class.set_annotations(next_anchor_prefix, f"{index + 1}")

    # PyModule.summary_lines():
    def summary_lines(self) -> Tuple[str, ...]:
        """Return PyModule summary lines."""
        # Create the Title
        lines: List[str] = []
        if self.Name == "__init__":
            # Package is the top level doc string only.
            lines.extend(self.Lines)  # pragma: no unit cover
        else:
            lines.append(f"# {self.Name}: {self.Lines[0]}")
            lines.extend(self.Lines[1:])
            lines.append("")
            if self.Classes:
                lines.append("## Table of Contents (alphabetical order):")
                lines.append("")

            # Fill in the rest of the table of contents:
            py_class: PyClass
            next_indent: str = ""
            for py_class in self.Classes:
                lines.extend(py_class.summary_lines(next_indent))
            lines.append("")
        return tuple(lines)

    # PyModule.documentation_lines():
    def documentation_lines(self, prefix: str) -> Tuple[str, ...]:
        """Return the PyModule documentation lines."""
        # lines: Tuple[str, ...]  = self.Lines
        # doc_lines: List[str] = [f"{prefix} <a name=\"{self.Anchor}\"></a>{lines[0]}", ""]
        # doc_lines.extend(lines[1:])

        doc_lines: List[str] = []
        next_prefix: str = prefix + "#"
        py_class: PyClass
        for py_class in self.Classes:
            doc_lines.extend(py_class.documentation_lines(next_prefix))
        doc_lines.append("")
        return tuple(doc_lines)

    # PyModule.generate():
    def generate(self, markdown_path: Path, markdown_program: str, tracing: str = "") -> None:
        """Generate the markdown and HTML files."""
        # Compute *markdown_lines*:
        # next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>PyModule.generate({markdown_path}, {markdown_program})")
        module_summary_lines: Tuple[str, ...] = self.summary_lines()
        module_documentation_lines: Tuple[str, ...] = self.documentation_lines("#")
        markdown_lines: Tuple[str, ...] = (
            module_summary_lines + module_documentation_lines + ("",))

        # Make sure that the *docs_directory* actually exists:
        docs_directory: Path = markdown_path.parent
        if not docs_directory.is_dir():
            if tracing:
                print(f"{tracing}Creating {docs_directory=}")
            docs_directory.mkdir(parents=True, exist_ok=True)  # pragma: no unit cover

        # Write *markdown_lines* out to *markdown_path* file:
        try:
            markdown_file: IO[str]
            if tracing:
                print(f"{tracing}Writing out {markdown_path}")
            # FIXME: Gross hack!!!
            with open("README.md", "w") as markdown_file:
                markdown_file.write("\n".join(markdown_lines))
        except IOError:  # pragma: no unit covert
            raise RuntimeError(f"Unable to write to {markdown_path}")

        # Run *markdown_program*:
        if markdown_program:
            html_path: Path = markdown_path.with_suffix(".html")
            arguments: Tuple[str, ...] = (
                markdown_program, str(markdown_path))
            if tracing:
                print(f"{tracing}{arguments=}")
            html_file: IO[bytes]
            with open(html_path, "wb") as html_file:
                result: subprocess.CompletedProcess
                result = subprocess.run(arguments, capture_output=True)
                output: bytes = result.stdout
                assert isinstance(output, bytes)
                html_file.write(output)
        if tracing:
            print(f"{tracing}<=PyModule.generate({markdown_path}, {markdown_program})")


# PyFile:
@dataclass
class PyFile:
    """PyFile: A class that is one-to-one with a Python file.

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

    """

    py_path: Path
    md_path: Path
    html_path: Path
    markdown_program: Optional[str]
    detects_main: bool = field(init=False)
    has_main: bool = field(init=False)

    # PyFile.__post_init__():
    def __post__init__(self) -> None:
        """Finish initializing a PyFile."""
        self.detects_main = False
        self.has_main = False
        file: IO[str]
        lines: List[str]
        with open(self.py_path, "r") as file:
            lines = "/n".split(file.read())
        line: str
        for line in lines:
            if line.startswith("def main("):
                self.has_main = True
            elif (line.startswith("if __name__ == ")
                  and line[-1] == ":" and line[-6:-1] == "__main__"):
                self.detects_main = True

    # PyFile.process():
    def process(self, modules: "List[PyModule]", errors: List[str], tracing: str = "") -> None:
        """Process a PyFile.

        Arguments:
        * modules (List[PyModule]): A list to collect all PyModules onto.
        * errors (List[str]): A list to collect any generated errors on.

        Process the PyFile (*self*) and append the generated PyModule to *modulues*.
        Any error message lines are append to *error*s.

        """
        next_tracing = tracing + " " if tracing else ""
        module_name: str = f"{self.py_path}"
        if tracing:
            print(f"{tracing}=>PyFile.process({module_name}, *")

        module: Any = None  # TODO: figure out what the real type is.
        try:
            module = importlib.import_module(f"{self.py_path.stem}")
        except ModuleNotFoundError as module_not_found_error:  # pragma: no unit cover
            errors.append(f"Unable to open module '{module_name}': {str(module_not_found_error)}")
        except TypeError as type_error:  # pragma: no unit cover
            errors.append(f"Error with import of module '{module_name}: {str(type_error)}")
        if module is None:  # pragma: no unit cover
            errors.append(f"Unable to open module {module_name}: Not clear why")

        py_module: PyModule = PyModule(module)
        py_module.set_annotations("", "")
        md_path: Path = self.md_path
        try:
            py_module.generate(md_path, f"{self.markdown_program}", tracing=next_tracing)
        except RuntimeError as runtime_error:  # pragma: no unit cover
            errors.append(f"{md_path}: runtime error {runtime_error}")
        modules.append(py_module)

        if tracing:
            print(f"{tracing}<=PyFile.process({module_name}, *, *")


# PyPackage:
@dataclass
class PyPackage(PyBase):
    """PyPackage: Represents a Python package `__init.py__` file.

    Inherited Attributes:
    * *Name* (str): The package name (i.e name of directory containing the `__init__.py` file.)
    * *Lines* (Tuple[str, ...) , *Anchor*, *Number* from PyBase.

    Attributes:
    * *Class* (Any): The underlying Python class object that is imported.
    * *Functions* (Tuple[PyFunction, ...]): The various functions associated with the Class.

    Constructor:
    * PyPackage()

    """

    Class: Any = field(repr=False)
    Functions: Tuple[PyFunction, ...] = field(init=False, default=())


# Arguments:
@dataclass
class Arguments:
    """Arguments: A class for processing command line arguments.

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

    """

    arguments: Tuple[str, ...]
    python_files: List[PyFile] = field(init=False)
    errors: List[str] = field(init=False)
    unit_test: bool = field(init=False)
    markdown_program: Optional[str] = field(init=False)
    sorted_python_files: Tuple[PyFile, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Process the command line arguments and generate any associated PyFile's and errors.

        * *arguments* (Tuple[str, ...]):
          The command line arguments consist of a sequence of `.py` files, directory names and
          optional intermixed flags.   This is typically specified as `sys.argv[1:]` which
          excludes the initial program name.  If no `.py` files or directories are specified,
          the current directory is scanned for Python files.
          The supported flags are:
          * `--markdown=MARKDOWN`:
            The program used to convert a markdown file (`.md`) into an HTML (`.html) file.
            If not specified, the [`cmark`](https://cmark.docsforge.com/) program is used if
            it is available.
          * `--docs=DOCS_DIR`:
            The directory to store subsequently generated `.md` and `.html`
          * `--unit-test`:

        """
        # Initialize the remaining Arguments attributes.
        self.python_files = []
        self.errors = []
        self.unit_test = False
        self.markdown_program = None
        self.sorted_python_files = ()

        # Default to `cmark` program.  Default to None if not found.
        markdown_program: Optional[str] = shutil.which("cmark")
        if markdown_program:
            self.markdown_program = markdown_program

        # Figure out the initial *docs_directory*.  Try `docs`, `/tmp/`, and `.`:
        current_working_directory: Path = Path.cwd()
        docs_directory: Path
        for docs_directory in (
                current_working_directory / "docs", Path("/tmp"), current_working_directory):
            if docs_directory.is_dir():
                break
        else:  # pragma: no unit cover
            self.errors.append("No docs directory found")

        # Scan *arguments* from left to right:
        directory_flag_prefix: str = "--docs="
        markdown_flag_prefix: str = "--markdown="
        python_path: Path
        argument: str
        for argument in self.arguments:
            if argument.startswith("--"):
                if argument.startswith(directory_flag_prefix):
                    # directory=
                    directory_flag: str = argument[len(directory_flag_prefix):]
                    new_docs_directory: Path = Path(directory_flag)
                    if not new_docs_directory.is_dir():
                        self.errors.append(f"{directory_flag} is not a directory")
                    elif not os.access(directory_flag, os.W_OK):
                        self.errors.append(f"Directory {directory_flag} is not writable")
                    else:
                        docs_directory = new_docs_directory
                elif argument.startswith(markdown_flag_prefix):
                    # markdown=
                    markdown_flag: str = argument[len(markdown_flag_prefix):]
                    new_markdown_program: Optional[str] = shutil.which(markdown_flag)
                    if new_markdown_program:
                        self.markdown_program = new_markdown_program
                    else:
                        self.errors.append(f"{markdown_flag} program does not exist")
                elif argument == "--unit-test":
                    self.unit_test = True
                else:
                    self.errors.append(f"{argument} not a valid flag")
            elif argument.endswith(".py"):
                python_path = Path(argument)
                if python_path.exists():
                    py_base: str = argument[:-3]
                    md_path: Path = docs_directory / f"{py_base}.md"
                    html_path: Path = docs_directory / f"{py_base}.html"
                    print(f"---------->{docs_directory=} {md_path=} {html_path=}")
                    python_file = PyFile(python_path, md_path, html_path, markdown_program)
                    self.python_files.append(python_file)
                else:
                    self.errors.append(f"{argument} Python file does not exist")
            else:
                directory_path: Path = Path(argument)
                if directory_path.is_dir():
                    self.scan_directory(directory_path, docs_directory)
                else:
                    self.errors.append(f"{argument} is not a directory")

        # If no Python files are specified scan the current working directory.
        if not self.python_files:
            self.scan_directory(current_working_directory, docs_directory)

        python_files_table: Dict[Path, PyFile] = {python_file.py_path: python_file
                                                  for python_file in self.python_files}
        sorted_py_paths: Tuple[Path, ...] = tuple(
            sorted(python_file.py_path for python_file in self.python_files))
        py_path: Path
        self.sorted_python_files = tuple(python_files_table[py_path] for py_path in sorted_py_paths)

    # Arguments.scan_directory():
    def scan_directory(self, directory_path: Path, docs_directory: Path, tracing: str = "") -> None:
        """Scan directory for Python files.

        Arguments:
        * *directory_path* (Path):
           The directory to scan for Python files.  If no Python files are found, generate an error.
        * *docs_directory* (Path):
           The directory path to write .md and .html into.

        Returns:
        * Nothing

        """
        for python_path in directory_path.glob("*.py"):
            python_base: str = python_path.stem
            html_path: Path = docs_directory / f"{python_base}.html"
            md_path: Path = docs_directory / f"{python_base}.md"
            python_file: PyFile = PyFile(
                python_path, md_path, html_path, self.markdown_program)
            self.python_files.append(python_file)
        else:
            self.errors.append(f"There are no Python (.py) files in {directory_path}")

    # Arguments.unit_tests():
    def unit_tests(self, tracing: str = ""):
        """Run unit tests on Arguments."""
        # Test the argument parsing.
        # next_tracing: str = tracing + " " if tracing else ""
        print(f"{tracing}=>unit_tests()")
        arguments: Arguments
        temporary_directory: str
        with tempfile.TemporaryDirectory() as temporary_directory:
            arguments = Arguments((
                "--docs=no_docs",  # Non-existent directory.
                "--docs=docstrex.py",  # Exists as a file, but it is not a directory.
                "--docs=/",  # This is a directory but should not be writable.
                "--docs=docs",  # This should be a valid writable directory.
                f"--docs=f{temporary_directory}",  # Empty directory, generates an error.
                "--markdown=nomark",  # Non-existent executable, generates and error.
                "--markdown=ls",  # Exists as executable, so no error, but `ls` won't actually work.
                "--markdown=cmark",  # Exists as executable, and should work just fine.
                "--unit-test",  # Should work.
                "--bad-flag=foo",  # Should generate a bad flag error
                "missing_py.py",  # Missing .py file error should be generated.
                "docstrex.py",  # Would work as a valid executable.
                "nodir",  # Not a directory to scan.
                "docs",  # Technically, there should be no .py files in docs
            ))
        assert arguments.unit_test
        errors: Tuple[str, ...] = tuple(arguments.errors)
        assert len(errors) == 9, len(errors)
        assert errors[0] == "no_docs is not a directory", errors[0]
        assert errors[1] == "docstrex.py is not a directory", errors[1]
        assert errors[2] == "Directory / is not writable", errors[2]
        assert errors[3].endswith(" is not a directory"), errors[3]
        assert errors[4] == "nomark program does not exist", errors[4]
        assert errors[5] == "--bad-flag=foo not a valid flag", errors[5]
        assert errors[6] == "missing_py.py Python file does not exist", errors[6]
        assert errors[7] == "nodir is not a directory", errors[7]
        assert errors[8] == "There are no Python (.py) files in docs", errors[8]

        # If no python files are listed, the current working directory is scanned.
        arguments = Arguments(())
        errors = tuple(arguments.errors)
        assert errors[0].startswith("There are no Python (.py) files in "), errors[0]

        print(f"{tracing}<=unit_tests()")

    # if not non_flag_arguments:  # Scan current directory.
    #     non_flag_arguments.append(".")  # pragma: no unit cover

    # module_names: Set[str] = set()
    # for argument in non_flag_arguments:
    #     if argument.endswith(".py"):
    #         module_names.add(argument[:-3])
    #     elif Path(argument).is_dir():  # pragma: no unit cover
    #         paths = tuple(Path(argument).glob("*.py"))
    #         python_path: Path
    #     else:  # pragma: no unit cover
    #         module_names.add(argument)

    # # __init__.py get imported as a side-effect of reading the other packages.
    # # Thus, if "__init__" is *py_names*, it must be the first module opened.
    # first_module: Tuple[str, ...] = ()
    # if "__init__" in module_names:
    #     module_names.remove("__init__")
    #     first_module = ("__init__",)
    # sorted_module_names: Tuple[str, ...] = first_module + tuple(sorted(module_names))
    # return tuple(sorted_module_names), documents_directory, markdown_program


def main(tracing: str = "") -> int:
    """Generate markdown files from Python document strings."""
    # Process the command line arguments:
    # module_names: Tuple[str, ...] = ("Not Updated",)
    next_tracing = tracing + " " if tracing else ""
    print(f"{tracing}=>main()")
    document_directory: Path
    markdown_program: str

    command_line_arguments: Tuple[str, ...] = tuple(sys.argv[1:])
    arguments: Arguments = Arguments(command_line_arguments)
    if arguments.unit_test:
        arguments.unit_tests(tracing=next_tracing)

    # Temporary:
    arguments2: Arguments2 = Arguments2(command_line_arguments)
    print(100 * "<")
    arguments2.run_unit_tests(tracing=next_tracing)
    print(100 * ">")

    sorted_python_files: Tuple[PyFile, ...] = arguments.sorted_python_files
    sorted_python_paths: Tuple[Path, ...] = tuple(
        python_file.py_path for python_file in sorted_python_files)
    if tracing:
        print(f"{tracing}{sorted_python_paths=}")

    modules: List[PyModule] = []
    errors: List[str] = []
    for python_file in sorted_python_files:
        python_file.process(modules, errors, tracing=next_tracing)

    for error in errors:
        print(error)  # pragma: no unit cover
    return_code: int = int(len(errors) != 0)
    print(f"{tracing}<=main()")
    return return_code


@dataclass
class Arguments2:
    """Arguments2: The new and improved arguments scanner.

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
    """

    arguments: Sequence[str]
    errors: List[str] = field(init=False)
    markdown_path: Optional[Path] = field(init=False)
    output_path: Path = field(init=False)
    python_paths: List[Path] = field(init=False)
    package_paths: List[Path] = field(init=False)
    unit_tests: bool = field(init=False)

    # Arguments2.__post_init__():
    def __post_init__(self) -> None:
        """Perform Arguments2 post initialization."""
        # Ensure that all attributes are initialized:
        self.arguments = tuple(self.arguments)  # Make sure no accidental changes occur
        self.errors = []
        self.markdown_path = None
        which_markdown: Optional[str] = shutil.which("markdown")
        if which_markdown:
            self.markdown_path = Path(which_markdown)
        readme: Path = Path("README.md")
        if Arguments2.check_file_writable(str(readme)):
            self.output_path = readme
        self.python_paths = []
        self.package_paths = []
        self.unit_tests = False

        # Process the argments in a separate method that is easier to debub.
        self.process_arguments("__post_init")

    # Arguments2.process_arguments():
    def process_arguments(self, label: str, tracing: str = ""):
        """Process the arguments for an Arguments2 object."""
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print("")
            print(f"{tracing}=>Arguments2.process_arguments('{label}')")

        # Execute each process method in turn until one succeeds:
        errors: List[str] = self.errors
        argument: str
        index: int
        for index, argument in enumerate(self.arguments):
            # Attempt to process each different argument flag and stop after first one succeeds.
            if tracing:
                print(f"{tracing}Argument[{index}]: {argument}")
            if self.match_markdown_flag(argument, tracing=next_tracing):
                pass
            elif self.match_output_flag(argument, tracing=next_tracing):
                pass
            elif self.match_unit_tests_flag(argument, tracing=next_tracing):
                pass
            elif self.match_file_or_directory(argument, tracing=next_tracing):
                pass
            else:
                file_or_dir: Path = Path(argument)
                if not file_or_dir.exists():
                    errors.append(f"{file_or_dir} is neither a file nor directory")
                elif file_or_dir.is_dir():
                    self.scan_directory(file_or_dir, errors)
                else:
                    errors.append(f"Unable to process argument '{argument}'")
        if not self.python_paths:
            self.scan_directory(Path("."), errors)

        if tracing:
            print(f"{tracing}<=Arguments2.process_arguments('{label}')")

    # Arguments2.match_markdown_flag():
    def match_markdown_flag(self, argument: str, tracing: str = "") -> bool:
        """Match the `markdown=...` flag.

        Args:
        * argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        print(f"{tracing}=>>Arguments2.match_markdown_flag()")
        MARKDOWN_PREFIX: str = "--markdown="
        print(f"{tracing}Arguments2._march_markdown_flag: {argument=}")
        match: bool = False
        if argument.startswith(MARKDOWN_PREFIX):
            markdown_text: str = argument[len(MARKDOWN_PREFIX):]
            markdown_file: Optional[str] = shutil.which(markdown_text)
            if markdown_file:
                self.markdown_path = Path(markdown_file)
                # assert False, f"{argument=} {markdown_text=} {markdown_path=} {self.markdown=}"
                match = True
            else:
                self.errors.append(f"'{argument}': {markdown_text} executable not found")
        print(f"{tracing}<=Arguments2.match_markdown_flag()=>{match}")
        return match

    # Arguments2.match_output_flag():
    def match_output_flag(self, argument: str, tracing: str = "") -> bool:
        """Match a 'output=...' flag.

        Args:
            argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        if tracing:
            print(f"{tracing}=>Arguments2.match_output_flag()")
        OUTPUT_PREFIX: str = "--outfile="
        match: bool = False
        if argument.startswith(OUTPUT_PREFIX):
            output_path: Path = Path(argument[len(OUTPUT_PREFIX):])
            if self.check_file_writable(str(output_path)):
                self.output_path = output_path
                match = True
            else:
                self.errors.append(f"Unable to write to {output_path}")
        if tracing:
            print(f"{tracing}<=Arguments2.match_output_flag()=>{match}")
        return match

    # Arguments2.match_unit_tests():
    def match_unit_tests_flag(self, argument, tracing: str = "") -> bool:
        """Match --unit-tests flag.

        Args:
            argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        if tracing:
            print(f"{tracing}=>Arguments2.match_unit_tests()")
        match: bool = argument == "--unit-tests"
        if match:
            self.unit_tests = True
        if tracing:
            print(f"{tracing}<=Arguments2.match_unit_tests()=>{match}")
        return match

    # Arguments2.match_file_or_directory():
    def match_file_or_directory(self, argument: str, tracing: str = "") -> bool:
        """Process an argument if it is file or directory.

        Arguments:
            file_name (str): The file name to check for writable.

        Returns:
            True if writable and False otherwise.
        """
        # next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>Arguments2._match_file_or_directory('{argument}')")

        path: Path = Path(argument)
        match: bool = False
        if path.exists():
            if path.suffix == ".py":
                self.python_paths.append(Path(path))
                match = True
            elif path.is_dir():
                match = self.scan_directory(path, self.errors)

        if not match:
            self.errors.append(
                f"'{argument}' is neither Python file, package, nor directory.")

        if tracing:
            print(f"{tracing}<=Arguments2._match_file_or_directory('{argument}') => "
                  f"{match} {self.errors}")
        return match

    # Arguments2.scan_directory():
    def scan_directory(self, directory: Path, errors: List[str], tracing: str = "") -> bool:
        """Scan a directory for Python files.

        Args:
        * directory (Path): The directory of Pythongfiles to process.
        * errors (List[str]): An error list to append errors to.

        Returns:
        * (bool): True for sucess and False otherwise:

        """
        if tracing:
            print(f"{tracing}=>Arguments2.scan_directory()")
        assert directory.is_dir(), f"{directory} is not a directory"
        match: bool = False

        file_path: Path
        for file_path in directory.glob("*.py"):
            if file_path.suffix == ".py":
                self.python_paths.append(file_path)
                match = True
            if file_path.name == "__init__.py":
                self.package_paths.append(directory)
        if not match:
            self.errors.append(f"{directory} does not contain any Python files")
        if tracing:
            print(f"{tracing}=>Arguments2.scan_directory()=>{match}")
        return match

    # Arguments2.check_file_writable():
    @staticmethod
    def check_file_writable(file_name: str) -> bool:
        """Check if a file is writable.

        Arguments:
            file_name (str): The file name to check for writable.

        Returns:
            True if writable and False otherwise.

        """
        # See [Section 3.2](https://www.novixys.com/blog/python-check-file-can-read-write/):
        if os.path.exists(file_name):
            # path exists
            if os.path.isfile(file_name):  # is it a file or a dir?
                # also works when file is a link and the target is writable
                return os.access(file_name, os.W_OK)
            else:
                return False  # path is a dir, so cannot write as a file

        # target does not exist, check perms on parent dir
        pdir = os.path.dirname(file_name)
        if not pdir:
            pdir = '.'  # pragma: no unit cover
        # target is creatable if parent dir is writable
        return os.access(pdir, os.W_OK)

    # Arguments2.run_unit_tests():
    def run_unit_tests(self, tracing: str = "") -> None:
        """Run Arguments2 unit tests."""
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>Arguments2.run_unit_tests()")
            print(f"{tracing}{self.arguments=}")

        # Checkout check_file_writable() method:
        assert Arguments2.check_file_writable("README.md"), "Writable README.md failed."
        assert not Arguments2.check_file_writable("/"), "Root should not be writable"
        assert not Arguments2.check_file_writable("/tmp"), "Overwrite of dir should not be allowed"
        assert not Arguments2.check_file_writable("/nodir"), "Write into root not allowed"
        assert Arguments2.check_file_writable("/tmp/foo.bar"), "Write into /tmp allowed"

        def check_error(arguments: Sequence[str], want_error: str, tracing: str = "") -> None:
            """Verify that an error message is generated."""
            print(f"{tracing}=>Arguments2.check_error({arguments}, '{want_error}')")
            arguments2: Arguments2 = Arguments2(arguments)
            if tracing:
                print(f"{tracing}{self.errors=}")
            assert len(arguments2.errors) >= 1, (
                f"{arguments} did not generate an error '{want_error}'")
            got_error: str = arguments2.errors[0]
            assert got_error == want_error, f"Error mismatch \n{want_error=}\n {got_error=}"
            print(f"{tracing}<=Arguments2.check_error({arguments}, '{want_error}')")

        # foo.py does not exist:
        check_error(["foo.py"],
                    "'foo.py' is neither Python file, package, nor directory.",
                    tracing=next_tracing)
        # test/package2 exists but does not have a `__init__.py` in it:
        check_error(["test/package2"],
                    "test/package2 does not contain any Python files", tracing=next_tracing)

        # `test/package1` does have an `__init__.py` files, so this should work:
        args2: Arguments2 = Arguments2(["test/package1"])
        args2.process_arguments('test/package1', tracing=next_tracing)
        path0: Path = args2.package_paths[0]
        assert f"{str(path0)}" == "test/package1", "somehow test/package1 is not OK "

        # Test that "--markdown=" works:
        args2 = Arguments2(["--markdown=cmark"])  # This assumes `cmark` is isntalled.
        args2.process_arguments("--markdown=cmark", tracing=next_tracing)
        assert isinstance(args2.markdown_path, Path)
        assert f"{args2.markdown_path.name}" == "cmark", (
            f"{args2.markdown_path.name} does not match 'cmark'")
        check_error(["--markdown=LICENSE"],
                    "'--markdown=LICENSE': LICENSE executable not found", tracing=next_tracing)

        # Test that "--outfile=" works:
        args2 = Arguments2(["--outfile=/tmp/README.md"])
        args2.process_arguments("-outile=/tmp/README.md", tracing=next_tracing)
        tmp_readme_md: Path = Path("/tmp/README.md")
        assert f"{args2.output_path}" == f"{tmp_readme_md}", (
            f"'{args2.output_path}' != '{tmp_readme_md}'")
        check_error(["--outfile=/bogus.md"], "Unable to write to /bogus.md", tracing=next_tracing)

        # Test that "--unit-tests" works:
        args2 = Arguments2(["--unit-tests"])
        args2.process_arguments("--unit-tests", tracing=next_tracing)
        assert args2.unit_tests, "--unit-tests did not work"

        # Test that explicitly specifying .py file works:
        args2 = Arguments2(["docstrex.py"])
        args2.process_arguments("docstrex.py", tracing=next_tracing)
        assert not args2.errors, "Unexpexted errors found"
        assert args2.python_paths
        python_path0: Path = args2.python_paths[0]
        assert python_path0.name == "docstrex.py", f"Found {python_path0} instead of docstrex.py"

        # Test that no arguments works:
        args2 = Arguments2([])
        args2.process_arguments("empty", tracing=next_tracing)
        markdown_path: Optional[Path] = args2.markdown_path
        assert isinstance(markdown_path, Path)
        assert f"{markdown_path.name}" == "markdown", args2
        output_path: Path = args2.output_path
        assert f"{output_path}" == "README.md", args2
        assert not args2.unit_tests, args2
        assert len(args2.errors) == 0, args2
        assert len(args2.arguments) == 0, args2.arguments
        assert len(args2.python_paths) == 2, args2  # __init__.py and docstrx.py

        # Test that bogus file gets flagged as an error:
        check_error(["test/error.txt"],
                    "'test/error.txt' is neither Python file, package, nor directory.",
                    tracing=next_tracing)

        if tracing:
            print(f"{tracing}<=Arguments2.run_unit_tests()")


"""
    # For each *module_name*, import it, generate documentation, and write it out:
    modules: List[PyModule] = []
    module_name: str
    for module_name in module_names:
        # Import each Module Name and process it:
        module: Any = None
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as module_not_found_error:  # pragma: no unit cover
            print(f"Unable to open module '{module_name}': {str(module_not_found_error)}")
            return 1
        except TypeError as type_error:  # pragma: no unit cover
            print(f"Error with import of module '{module_name}: {str(type_error)}")
        if module is None:  # pragma: no unit cover
            print(f"Unable to open module '{module_name}': Not clear why")
            return 1

        py_module: PyModule = PyModule(module)
        py_module.set_annotations("", "")
        modules.append(py_module)

        # Generate Markdown and HTML files:
        try:
            py_module.generate(document_directory, markdown_program)
        except RuntimeError as runtime_error:  # pragma: no unit cover
            print(runtime_error)
            return 1

    return 0
"""

if __name__ == "__main__":
    main(tracing=" ")
