#!/usr/bin/env python3
"""DOCument STRing EXtract -- Convert Python doc strings to markdown.

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

"""

# <----------------------------- 80 characters -----------------------------> #


from dataclasses import dataclass, field
import importlib
import inspect
import os
from pathlib import Path
import shutil  # Used for shutil.which()
import subprocess  # Used to execute the .md => .html converter program.
import sys
from typing import Any, Callable, cast, Dict, IO, List, Optional, Sequence
from typing import Set, Tuple


# PyBase:
@dataclass
class PyBase(object):
    """PyBase: Base class of PyFunction, PyClass, PyModule, and PyPackage.

    Attributes:
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

    Constructor: PyBase()

    """

    name: str = field(init=False, default="")
    lines: Tuple[str, ...] = field(init=False, repr=False, default=())
    anchor: str = field(init=False, repr=False, default="")
    number: str = field(init=False, repr=False, default="??")

    # PyBase.set_lines():
    def set_lines(self, doc_string: Optional[str]) -> None:
        """Set the Lines field of a PyBase.

        Arguments:
        * *doc_string* (Optional[str]):
           A raw documentation string or None if no documentation string is
           present.

        *doc_string* is split into lines.  Both the first line and all
        subsequent empty lines are used to determine the actual doc string
        indentation level.  The approproiate lines have their indentation
        padding removed before being stored into PyBase.Lines attributes.

        """
        self.lines = ("NO DOC STRING!",)
        if doc_string:
            line: str
            lines: List[str] = [
                line.rstrip() for line in doc_string.split("\n")]

            # Compute the *common_indent* in spaces ignoring empty lines:
            big: int = 123456789
            common_indent: int = big
            # The first line of a doc string has no indentation padding,
            # but all other lines do.
            for line in lines[1:]:
                indent: int = len(line) - len(line.lstrip())
                if line:  # Skip empty lines:
                    common_indent = min(common_indent, indent)
            if common_indent == big:
                common_indent = 0

            # Convert "NAME: Summary line." => "Summary_line.":
            first_line: str = lines[0]
            pattern: str = f"{self.name}: "
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
                del lines[1]

            self.lines = tuple(lines)

    # PyBase.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the PyBase Anchor and Number attributes.

        Arguments:
        * *anchor_prefix* (str):
          The string to prepend to the document element name before setting
          the Anchor attribute.
        * *number_prefix* (str):
          The string to prepend to the document element name before setting
          the Number attribute.

        This method must be implemented by sub-classes.

        """
        raise NotImplementedError(
            f"{self}.set_annotations() is not implemented.")


# PyFunction:
@dataclass
class PyFunction(PyBase):
    """PyFunction: Represents a function or method.

    Inherited Attributes:
    * *name* (str)
    * *lines* (Tuple[str, ...])
    * *anchor* (str)
    * *number* (str)

    Attributes:
    *  *function* (Callable): The actual function/method object.

    Constructor:
    * PyFunction(name, lines, anchor, number, function)

    """

    function: Callable

    # PyFunction.__post_init__():
    def __post_init__(self) -> None:
        """Post process a PyFunction."""
        function: Callable = self.function
        if hasattr(function, "__name__"):
            self.name = getattr(function, "__name__")
        if hasattr(function, "__doc__"):
            self.set_lines(getattr(function, "__doc__"))

    # PyFunction.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the markdown annotations.

        (see [ModeDoc.set_annoations](#Doc-PyBase-set_annotations)

        """
        self.anchor = anchor_prefix + self.name.lower().replace("_", "-")
        self.number = number_prefix

    # PyFunction.summary_lines():
    def summary_lines(self, class_name: str, indent: str) -> Tuple[str, ...]:
        """Return PyModule table of contents summary lines.

        Arguments:
        * *class_name*: The class name the function is a member of.
        * *indent* (int) The prefix spaces to make the markdown work.

        Returns:
        * (Tuple[str, ...]): The resulting summary lines.

        """
        assert self.lines, f"{class_name=}"
        return (f"{indent}* {self.number} [{self.name}()]"
                f"(#{self.anchor}): {self.lines[0]}",)

    # PyFunction.documentation_lines():
    def documentation_lines(self,
                            class_name: str, prefix: str) -> Tuple[str, ...]:
        """Return the PyModule documentation lines.

        Arguments:
        * *class_Name* (str): The class name to use for methods.
        * *prefix* (str): The prefix to use to make the markdown work.

        Returns:
        * (Tuple[str, ...]): The resulting documentations lines

        """
        lines: Tuple[str, ...] = self.lines
        signature: inspect.Signature = inspect.Signature.from_callable(
            self.function)
        doc_lines: Tuple[str, ...] = (
            (f"{prefix} <a name=\"{self.anchor}\"></a>{self.number} "
             f"`{class_name}.`{self.name}():"),
            "",
            f"{class_name}.{self.name}{signature}:",
            ""
        ) + lines + ("",)
        return doc_lines


# PyClass:
@dataclass
class PyClass(PyBase):
    """PyClass: Represents a class method.

    Inherited Attributes:
    * *name* (str): The attribute name.
    * *lines* (Tuple[str, ...]):
    * *anchor* (str):
    * *number* (str):

    Attributes:
    * *xclass* (Any): The underlying Python class object that is imported.
    * *functions* (Tuple[PyFunction, ...]): The various functions associated
       with the Class.

    Constructor:
    * PyClass()

    """

    xclass: Any = field(repr=False)
    Functions: Tuple[PyFunction, ...] = field(init=False, default=())

    # PyClass.__post_init__():
    def __post_init__(self) -> None:
        """Post process PyClass."""
        # Set Name and Lines attributes:
        if hasattr(self.xclass, "__name__"):
            self.name = cast(str, getattr(self.xclass, "__name__"))
        if hasattr(self.xclass, "__doc__"):
            self.set_lines(cast(str, getattr(self.xclass, "__doc__")))

        # Set the Functions attribute:
        py_functions: List[PyFunction] = []
        attribute_name: str
        attribute: Any
        for attribute_name, attribute in self.xclass.__dict__.items():
            if not attribute_name.startswith("_") and callable(attribute):
                py_functions.append(PyFunction(attribute))
        self.Functions = tuple(py_functions)

    # PyClass.set_annotations():
    def set_annotations(self, anchor_prefix: str, number_prefix: str) -> None:
        """Set the Markdown anchor."""
        anchor: str = anchor_prefix + self.name.lower().replace("_", "-")
        self.Anchor = anchor
        self.Number = number_prefix

        next_anchor_prefix: str = anchor_prefix + "--"
        py_function: PyFunction
        for index, py_function in enumerate(self.Functions):
            py_function.set_annotations(
                next_anchor_prefix, f"{number_prefix}.{index + 1}")

    # PyClass.summary_lines():
    def summary_lines(self, indent: str) -> Tuple[str, ...]:
        """Return PyModule summary lines."""
        lines: List[str] = [
            f"{indent}* {self.number} Class: [{self.name}](#{self.anchor}):"]
        next_indent: str = indent + "  "
        py_function: PyFunction
        for py_function in self.Functions:
            lines.extend(py_function.summary_lines(self.name, next_indent))
        return tuple(lines)

    # PyClass.documentation_lines():
    def documentation_lines(self, prefix: str) -> Tuple[str, ...]:
        """Return the PyModule documentation lines."""
        lines: Tuple[str, ...] = self.lines
        doc_lines: List[str] = [
            f"{prefix} <a name=\"{self.anchor}\">" +
            f"</a>{self.number} Class {self.name}:",
            "",
        ]
        doc_lines.extend(lines)
        doc_lines.append("")
        next_prefix: str = prefix + "#"
        function: PyFunction
        for function in self.Functions:
            doc_lines.extend(
                function.documentation_lines(self.name, next_prefix))
        doc_lines.append("")
        return tuple(doc_lines)


# PyModule:
@dataclass
class PyModule(PyBase):
    """PyModule: Represents a Python module (i.e. file).

    The generated Markdown anchor for the documentation element.
    It is of the form "MODULE--CLASS--FUNCTION", where the
    module/class/function names have underscores converted into hyphens.

    Inherited Attributes:
    * *name* (str):
    * *lines* (Tuple[str, ...]):
    * *anchor* (str):
    * *number* (str):

    New Attributes:
    * *module* (Any): The Python module object.
    * *classes* (Tuple[PyClass, ...]):
    #   The classes defined by the Python module object.

    Constructor:
    * PyModule(name, lines, anchor, number, module, classes)
    """

    module: Any = field(repr=False)
    classes: Tuple[PyClass, ...] = field(init=False, default=())

    # PyModule.__post_init__():
    def __post_init__(self) -> None:
        """Recursively extract information from an object."""
        module: Any = self.module

        # Get initial *module_name*:
        module_name: str = ""
        if hasattr(module, "__name__"):
            module_name = getattr(module, "__name__")
        is_package: bool = module_name == "__init__"

        # Change first string to enable package tracing.
        tracing: str = "." if is_package else ""
        if tracing:
            print(f"{tracing}Processing {module_name} {is_package=}")
        if hasattr(module, "__doc__"):
            doc_string = getattr(module, "__doc__")
            if tracing:
                print(f"{tracing}{doc_string=}")
            self.set_lines(doc_string)
            if is_package:
                first_line: str = self.lines[0]
                exit(1)
                colon_index: int = first_line.find(":")
                if colon_index >= 0:
                    module_name = first_line[:colon_index]
                    first_line = first_line[
                        colon_index + 2:]  # Skip over "...: "
                    self.Lines = (first_line, "") + self.lines[1:]

        # The Python import statement can import class to the module namespace.
        # We are only interested in classes that are defined in *module*:
        py_classes: List[PyClass] = []
        class_type: type = type(PyBase)  # Any class name to get class type.
        assert isinstance(class_type, type)
        attribute_name: str
        # print(f"{module=} {type(module)=}")
        for attribute_name in dir(module):
            if not attribute_name.startswith("_"):
                attribute: Any = getattr(module, attribute_name)
                if hasattr(attribute, "__module__"):
                    defining_module: Any = getattr(attribute, "__module__")
                    # print(f"{attribute_name=} "
                    #       f"{attribute=} {defining_module}")
                    if isinstance(attribute, class_type) \
                       and str(defining_module) == module_name:
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
            lines.extend(self.lines)  # pragma: no unit cover
        else:
            lines.append(f"# {self.Name}: {self.lines[0]}")
            lines.extend(self.lines[1:])
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
        # doc_lines: List[str] = [
        #   f"{prefix} <a name=\"{self.Anchor}\"></a>{lines[0]}", ""]
        # doc_lines.extend(lines[1:])

        doc_lines: List[str] = []
        next_prefix: str = prefix + "#"
        py_class: PyClass
        for py_class in self.Classes:
            doc_lines.extend(py_class.documentation_lines(next_prefix))
        doc_lines.append("")
        return tuple(doc_lines)

    # PyModule.generate():
    def generate(self, markdown_path: Path,
                 convert_path: Optional[Path],
                 html_path: Path, tracing: str = "") -> None:
        """Generate the markdown and HTML files."""
        # Compute *markdown_lines*:
        # next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>PyModule.generate({markdown_path}, "
                  f"{convert_path}, {html_path})")
        module_summary_lines: Tuple[str, ...] = self.summary_lines()
        module_documentation_lines: Tuple[str, ...] = \
            self.documentation_lines("#")
        markdown_lines: Tuple[str, ...] = (
            module_summary_lines + module_documentation_lines + ("",))

        # Make sure that the *docs_directory* actually exists:
        # docs_directory: Path = markdown_path.parent
        # if not docs_directory.is_dir():
        #     if tracing:
        #         print(f"{tracing}Creating {docs_directory=}")
        #     docs_directory.mkdir(parents=True,
        #        exist_ok=True)  # pragma: no unit cover

        # Write *markdown_lines* out to *markdown_path* file:
        try:
            markdown_file: IO[str]
            if tracing:
                print(f"{tracing}Writing out {markdown_path}")
            # FIXME: Gross hack!!!
            assert Arguments.check_file_writable(str(markdown_path)), (
                f"{markdown_path} is not writable")
            with open("README.md", "w") as markdown_file:
                markdown_file.write("\n".join(markdown_lines))
        except IOError:  # pragma: no unit covert
            raise RuntimeError(f"Unable to write to {markdown_path}")

        # Run *convert_path*:
        if convert_path:
            arguments: Tuple[str, ...] = (
                str(convert_path), str(markdown_path))
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
            print(f"{tracing}<=PyModule.generate("
                  f"{markdown_path}, {convert_path}, {html_path})")


# PyFile:
@dataclass
class PyFile:
    """PyFile: A class that is one-to-one with a Python file.

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
    * PyFile(python_path, markdown_path, convert_path, html_path)

    """

    python_path: Path
    convert_path: Optional[Path]
    markdown_path: Path
    html_path: Path
    detects_main: bool = field(init=False)
    has_main: bool = field(init=False)

    # PyFile.__post_init__():
    def __post__init__(self) -> None:
        """Finish initializing a PyFile."""
        self.detects_main = False
        self.has_main = False
        file: IO[str]
        lines: List[str]
        with open(self.python_path, "r") as file:
            lines = "/n".split(file.read())
        line: str
        for line in lines:
            if line.startswith("def main("):
                self.has_main = True
            elif (line.startswith("if __name__ == ")
                  and line[-1] == ":" and line[-6:-1] == "__main__"):
                self.detects_main = True

    # PyFile.process():
    def process(self, modules: "List[PyModule]", markdown_path: Path,
                convert_path: Optional[Path], html_path: Path,
                errors: List[str], tracing: str = "") -> None:
        """Process a PyFile.

        Arguments:
        * modules (List[PyModule]): A list to collect all PyModules onto.
        * markdown_path (Path}: The path for the `README.md` file.
        * convert_path (Optional(Path)):
          The path to the program to convert .md into .html.
        * html_path (Path): The path for the `README.html` file.
        * errors (List[str]): A list to collect any generated errors on.

        Process the PyFile (*self*) and append the generated PyModule to
        *modulxes*.  Any error message lines are append to *error*s.

        """
        next_tracing = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>PyFile.process("
                  f"{modules}, {markdown_path}, {convert_path}, {html_path})")

        python_path: Path = self.python_path
        module_name: str = python_path.stem
        module: Any = None  # TODO: figure out what the real type is.
        try:
            module = importlib.import_module(f"{module_name}")
        except ModuleNotFoundError as no_module_error:  # pragma: no unit cover
            errors.append(
                f"Unable to open module '{module_name}': "
                f"{str(no_module_error)}")
        except TypeError as type_error:  # pragma: no unit cover
            errors.append(
                f"Error with import of module '{module_name}: "
                f"{str(type_error)}")
        if module is None:  # pragma: no unit cover
            errors.append(
                f"Unable to open module {module_name}: Not clear why")

        py_module: PyModule = PyModule(module)
        py_module.set_annotations("", "")
        try:
            py_module.generate(markdown_path,
                               convert_path, html_path, tracing=next_tracing)
        except RuntimeError as runtime_error:  # pragma: no unit cover
            errors.append(f"{markdown_path}: runtime error {runtime_error}")
        modules.append(py_module)

        if tracing:
            print(f"{tracing}<=PyFile.process("
                  f"{modules}, {markdown_path}, {convert_path}, {html_path})")


# PyPackage:
@dataclass
class PyPackage(PyBase):
    """PyPackage: Represents a Python package `__init.py__` file.

    Inherited Attributes:
    * *Name* (str): The pkg name (i.e name of dir with the `__init__.py` file.)
    * *Lines* (Tuple[str, ...) , *Anchor*, *Number* from PyBase.

    Attributes:
    * *Class* (Any): The underlying Python class object that is imported.
    * *Functions* (Tuple[PyFunction, ...]): The functions of the Class.

    Constructor:
    * PyPackage()

    """

    Class: Any = field(repr=False)
    Functions: Tuple[PyFunction, ...] = field(init=False, default=())


def main(tracing: str = "") -> int:
    """Generate markdown files from Python document strings."""
    # Process the command line arguments:
    next_tracing = tracing + " " if tracing else ""
    if tracing:
        print(f"{tracing}=>main()")

    command_line_arguments: Tuple[str, ...] = tuple(sys.argv[1:])
    arguments: Arguments = Arguments(command_line_arguments)
    if tracing:
        print(f"{tracing}{arguments.arguments=}")
        print(f"{tracing}{arguments.directories=}")
        print(f"{tracing}{arguments.html=}")
        print(f"{tracing}{arguments.markdown=}")
        print(f"{tracing}{arguments.unit_tests=}")
    if arguments.unit_tests:
        arguments.run_unit_tests(tracing=next_tracing)
    return_code: int = arguments.process(tracing=next_tracing)

    if tracing:
        print(f"{tracing}<=main()=>{return_code}")
    return return_code


# Arguments:
@dataclass
class Arguments:
    """Arguments: Command line arguments scanner.

    Attributes:
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
    * Arguments(command_line_arguments)
    """

    arguments: Sequence[str]
    convert_path: Optional[Path] = field(init=False)
    directories: Dict[Path, Set[Path]] = field(init=False)
    errors: List[str] = field(init=False)
    html: bool = field(init=False)
    markdown: Optional[Path] = field(init=False)
    unit_tests: bool = field(init=False)
    tracing: str = " "

    # Arguments.__post_init__():
    def __post_init__(self) -> None:
        """Perform Arguments post initialization."""
        tracing: str = " "
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>Arguments.__post_init__()")

        # Ensure that all attributes are initialized:
        self.arguments = tuple(self.arguments)  # Ensure no more changes occur
        self.convert_path = None
        self.directories = {}
        self.errors = []
        self.html = False
        self.unit_tests = False
        self.tracing = " "  # Do tracing for now.
        self.unit_tests = False

        # Process the argments in a separate method that is easier to debug.
        self.process_further("Arguments.__post_init__", next_tracing)
        if tracing:
            print(f"{tracing}<=Arguments.__post_init__()")

    # Arguments.process_further():
    def process_further(self, label: str, tracing: str = ""):
        """Further process the arguments of an Arguments object."""
        # This function makes command line parser test suite easier.
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print("")
            print(f"{tracing}=>Arguments.process_further('{label}')")

        # Determine which markdown to HTML converter to default to.
        markdown: str
        for markdown in ("markdown", "cmark"):
            which: Optional[str] = shutil.which("markdown")
            if which:
                self.markdown = Path(which)
                break

        # Execute each process method in turn until one succeeds:
        errors: List[str] = self.errors
        argument: str
        index: int
        for index, argument in enumerate(self.arguments):
            # Attempt to process each different argument flag and stop after
            # first one succeeds.
            if tracing:
                print(f"{tracing}Argument[{index}]: {argument}")
            if self.match_convert_flag(argument, tracing=next_tracing):
                pass
            elif self.match_file_or_directory(argument, tracing=next_tracing):
                pass
            elif self.match_html_flag(argument, tracing=next_tracing):
                pass
            elif self.match_unit_tests_flag(argument, tracing=next_tracing):
                pass
            elif argument.startswith("--"):
                errors.append(
                    f"{argument} is not a recognized command line option")
            else:
                file_or_dir: Path = Path(argument)
                if not file_or_dir.exists():
                    errors.append(
                        f"{file_or_dir} is neither a file no`r directory")
                elif file_or_dir.is_dir():
                    self.scan_directory(file_or_dir, tracing=next_tracing)
                else:
                    errors.append(f"Unable to process argument '{argument}'")
        if not self.directories:
            self.scan_directory(Path("."), tracing=next_tracing)

        if tracing:
            print(f"{tracing}{self.arguments=}")
            print(f"{tracing}<=Arguments.process_further('{label}')")

    # Arguments.match_convert_flag():
    def match_convert_flag(self, argument: str, tracing: str = "") -> bool:
        """Match the `--convert=...` flag.

        Args:
        * argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        print(f"{tracing}=>>Arguments.match_convert_flag()")
        CONVERT_PREFIX: str = "--convert="
        print(f"{tracing}Arguments._march_convert_flag: {argument=}")
        match: bool = False
        if argument.startswith(CONVERT_PREFIX):
            markdown_text: str = argument[len(CONVERT_PREFIX):]
            markdown_file: Optional[str] = shutil.which(markdown_text)
            if markdown_file:
                self.markdown_path = Path(markdown_file)
                # assert False, (
                #    f"{argument=} {markdown_text=}"
                #    f" {markdown_path=} {self.markdown=}")
                match = True
            else:
                self.errors.append(
                    f"'{argument}': {markdown_text} executable not found")
        print(f"{tracing}<=Arguments.match_convert_flag()=>{match}")
        return match

    # Arguments.match_output_flag():
    def match_output_flag(self, argument: str, tracing: str = "") -> bool:
        """Match a 'output=...' flag.

        Args:
            argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        if tracing:
            print(f"{tracing}=>Arguments.match_output_flag()")
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
            print(f"{tracing}<=Arguments.match_output_flag()=>{match}")
        return match

    # Arguments.match_html_flag():
    def match_html_flag(self, argument, tracing: str = "") -> bool:
        """Match `--html` flag.

        Args:
            argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        if tracing:
            print(f"{tracing}=>Arguments.match_html_flag()")
        match: bool = argument == "--html"
        if match:
            self.html = True
        if tracing:
            print(f"{tracing}<=Arguments.match_html_flag()=>{match}")
        return match

    # Arguments.match_unit_tests():
    def match_unit_tests_flag(self, argument, tracing: str = "") -> bool:
        """Match --unit-tests flag.

        Args:
            argument (str): The argument to match against.

        Returns:
            True if a match is found and False otherwise.

        """
        if tracing:
            print(f"{tracing}=>Arguments.match_unit_tests()")
        match: bool = argument == "--unit-tests"
        if match:
            self.unit_tests = True
        if tracing:
            print(f"{tracing}<=Arguments.match_unit_tests()=>{match}")
        return match

    # Arguments.match_file_or_directory():
    def match_file_or_directory(self, argument: str, tracing: str = "") -> bool:
        """Process an argument if it is file or directory.

        Arguments:
            file_name (str): The file name to check for writable.

        Returns:
            True if writable and False otherwise.

        """
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(
                f"{tracing}=>Arguments._match_file_or_directory('{argument}')")

        path: Path = Path(argument)
        match: bool = False
        if path.exists():
            if path.is_dir():
                self.scan_directory(path, tracing=next_tracing)
            elif path.suffix == ".py":
                self.python_record(path)

        if not match:
            self.errors.append(
                f"'{argument}' is not Python file, package, or directory.")

        if tracing:
            print(f"{tracing}<=Arguments._match_file_or_directory"
                  f"('{argument}') => {match} {self.errors}")
        return match

    # Arguments.python_record():
    def python_record(self, python_path: Path) -> None:
        """Record the existance of Python file.

        Args:
        * *python_path* (Path): The path to the Python file.

        """
        assert python_path.suffix == ".py", (
            f"{python_path} is not a Python file.")
        directories: Dict[Path, Set[Path]] = self.directories
        parent_path: Path = python_path.parent
        if parent_path not in directories:
            directories[parent_path] = set()
        directories[parent_path].add(python_path)

    # Arguments.scan_directory():
    def scan_directory(self, directory: Path, tracing: str = "") -> bool:
        """Scan a directory for for Python files.

        Args:
            directory (Path): The directory to scan.

        Returns:
            (bool): True if a `.py` was encountered and `false` otherwise.

        """
        if tracing:
            print(f"{tracing}=>scan_directory({directory})")

        assert directory.is_dir(), f"{directory} is not a directory."
        python_path: Path
        for python_path in directory.glob("*.py"):
            self.python_record(python_path)
            match = True
        else:
            self.errors.append(f"No Python (`.py`) files found in {directory}")

        if tracing:
            print(f"{tracing}<=scan_directory({directory})=>{match}")
        return match

    # Arguments.check_file_writable():
    @staticmethod
    def check_file_writable(file_name: str) -> bool:
        """Check if a file is writable.

        Arguments:
            file_name (str): The file name to check for writable.

        Returns:
            True if writable and False otherwise.

        """
        # See [Section 3.2](
        #      https://www.novixys.com/blog/python-check-file-can-read-write/):
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

    # Arguments.run_unit_tests():
    def run_unit_tests(self, tracing: str = "") -> None:
        """Run Arguments unit tests."""
        next_tracing: str = tracing + " " if tracing else ""
        if tracing:
            print(f"{tracing}=>Arguments.run_unit_tests()")
            print(f"{tracing}{self.arguments=}")

        # Checkout check_file_writable() method:
        assert Arguments.check_file_writable(
            "README.md"), "Writable README.md failed."
        assert not Arguments.check_file_writable(
            "/"), "Root should not be writable"
        assert not Arguments.check_file_writable(
            "/tmp"), "Overwrite of dir should not be allowed"
        assert not Arguments.check_file_writable(
            "/nodir"), "Write into root not allowed"
        assert Arguments.check_file_writable(
            "/tmp/foo.bar"), "Write into /tmp allowed"

        def check_error(arguments: Sequence[str],
                        error: str, tracing: str = "") -> None:
            """Verify that an error message is generated."""
            print(f"{tracing}=>Arguments.check_error({arguments}, '{error}')")
            arguments2: Arguments = Arguments(arguments)
            if tracing:
                print(f"{tracing}{self.errors=}")
            assert len(arguments2.errors) >= 1, (
                f"{arguments} did not generate an error '{error}'")
            got_error: str = arguments2.errors[0]
            assert got_error == error, (
                f"Error mismatch \n{error=}\n {got_error=}")
            print(f"{tracing}<=Arguments.check_error({arguments}, '{error}')")

        # foo.py does not exist:
        check_error(["foo.py"],
                    "'foo.py' is neither Python file, package, nor directory.",
                    tracing=next_tracing)
        # test/package2 exists but does not have a `__init__.py` in it:
        check_error(["test/package2"],
                    "test/package2 does not contain any Python files",
                    tracing=next_tracing)

        # `test/package1` does have an `__init__.py` files,
        # so this should work:
        args: Arguments = Arguments(["test/package1"])
        # args.process_further("test/package1", tracing=next_tracing)
        path0: Path = Path("test/package1")
        assert path0 in self.directories, "somehow test/package1 is not OK "

        # Test that "--covert=" works:
        args = Arguments(["--convert=cmark"])  # Assumes `cmark` is installed.
        args.process_further("--convert=cmark", tracing=next_tracing)
        assert isinstance(args.convert_path, Path)
        assert f"{args.convert_path.name}" == "cmark", (
            f"{args.convert_path.name} does not match 'cmark'")
        check_error(["--markdown=LICENSE"],
                    "'--markdown=LICENSE': LICENSE executable not found",
                    tracing=next_tracing)

        # Test that "--outfile=" works:
        args = Arguments(["--outfile=/tmp/README.md"])
        args.process_further("-outfile=/tmp/README.md", tracing=next_tracing)
        tmp_readme_md: Path = Path("/tmp/README.md")
        assert f"{args.output_path}" == f"{tmp_readme_md}", (
            f"'{args.output_path}' != '{tmp_readme_md}'")
        check_error(["--outfile=/bogus.md"],
                    "Unable to write to /bogus.md", tracing=next_tracing)

        # Test that "--unit-tests" works:
        args = Arguments(["--unit-tests"])
        args.process_further("--unit-tests", tracing=next_tracing)
        assert args.unit_tests, "--unit-tests did not work"

        # Test that explicitly specifying .py file works:
        args = Arguments(["docstrex.py"])
        args.process_further("docstrex.py", tracing=next_tracing)
        assert not args.errors, "Unexpexted errors found"
        assert args.directories, "No paths are present"
        directory0: Set[Path] = tuple(args.directories.values())[0]
        python0: Path = tuple(directory0)[0]
        assert python0.name == "docstrex.py", (
            f"Found {python0} instead of `docstrex.py`")

        # Test that no arguments works:
        args = Arguments([])
        args.process_further("empty", tracing=next_tracing)
        markdown_path: Optional[Path] = args.markdown_path
        assert isinstance(markdown_path, Path)
        assert f"{markdown_path.name}" == "markdown", args
        output_path: Path = args.output_path
        assert f"{output_path}" == "README.md", args
        assert not args.unit_tests, args
        assert len(args.errors) == 0, args
        assert len(args.arguments) == 0, args.arguments
        directories: Dict[Path, Set[Path]] = args.directories
        cwd: Path = Path(".")
        assert cwd in directories, "Could not find `.` in directies"

        assert Path(".") in directories, "Could not find . in directies"
        directory0 = directories[Path(".")]
        error: str = f"{directory0} should only have two values."
        assert len(directory0) == 2, error
        assert Path("__init__.py") in directory0, (
            f"found {directory0}, not __init__.py and docstrx.py")
        # Test that bogus file gets flagged as an error:
        check_error(["test/error.txt"],
                    "'test/error.txt' is not Python file, package, or dir.",
                    tracing=next_tracing)

        if tracing:
            print(f"{tracing}<=Arguments.run_unit_tests()")
        return

    # Arguments.process():
    def process(self, tracing: str = "") -> int:
        """Process the command line Arguments."""
        next_tracing: str = tracing + " " if tracing else ""
        print(f"{tracing}=>Arguments.process()")

        convert_path: Optional[Path] = self.convert_path
        directories: Dict[Path, Set[Path]] = self.directories
        errors: List[str] = self.errors

        if tracing:
            print(f"{tracing}{convert_path=}")
            print(f"{tracing}{directories=}")

        # Scan through *sorted_directories*:
        sorted_directories: Tuple[Path, ...] = tuple(
            sorted(self.directories.keys()))
        modules: List[PyModule] = []
        index1: int
        python_directory: Path
        for index1, python_directory in enumerate(sorted_directories):
            markdown_path: Path = python_directory / "README.md"
            html_path: Path = python_directory / "README.html"
            sorted_python_paths: Tuple[Path, ...] = tuple(
                sorted(directories[python_directory]))

            python_path: Path
            index2: int
            for index2, python_path in enumerate(sorted_python_paths):
                python_file: PyFile = PyFile(python_path, convert_path,
                                             markdown_path, html_path)
                if tracing:
                    print(f"{tracing}PyFile[{index1}, {index2}]: {python_path}")
                python_file.process(modules, markdown_path, convert_path,
                                    html_path, errors, tracing=next_tracing)

        for error in errors:
            print(error)  # pragma: no unit cover
        return_code: int = int(len(errors) != 0)
        print(f"{tracing}<=Arugments.process()=>{return_code}")
        return return_code


"""
    # For each *module_name*, import it, generate documentation,
    # and write it out:
    modules: List[PyModule] = []
    module_name: str
    for module_name in module_names:
        # Import each Module Name and process it:
        module: Any = None
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as module_not_found_error: \
                                    # pragma: no unit cover
            print(f"Unable to open module '{module_name}': \
                   {str(module_not_found_error)}")
            return 1
        except TypeError as type_error:  # pragma: no unit cover
            print(f"Error with import of module '{module_name}: \
              {str(type_error)}")
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
