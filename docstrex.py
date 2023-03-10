#!/usr/bin/env python3
"""pyds2md: Convert Python doc strings to markdown and HTML files.

The program has [usage documentation](docs/__init__.py) stored in another file.
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
from typing import Any, Callable, cast, Dict, IO, List, Tuple, Optional


# PyBase:
@dataclass
class PyBase(object):
    """PyBase: Base class PyFunction, PyClass, PyModule, and PyPackage classes.

    Attributes:
    * *Name* (str):
       The element name (i.e. function/class/module name.)
    * *Lines* (Tuple[str, ...]):
       The documentation string converted into lines with extraneous indentation removed.
       This attribute is set by the *set_lines*() method.
    * *Anchor* (str):
       The generated Markdown anchor for the documentation element.
       It is of the form "MODULE--CLASS--FUNCTION", where the module/class/function names
       have underscores converted to hyphen.
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
        are ignored to determine the actual doc string indentation level.  The approproiate
        lines have there indentation padding removed before being stored into PyBase.Lines
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

            # Strip off blank lines between summary line an body:
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
    def generate(self, markdown_path: Path, markdown_program: str, tracing) -> None:
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
            with open(markdown_path, "w") as markdown_file:
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
    def scan_directory(self, directory_path: Path, docs_directory: Path) -> None:
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
