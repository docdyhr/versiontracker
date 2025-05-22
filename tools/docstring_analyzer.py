#!/usr/bin/env python3
"""Script to analyze docstrings in Python files and identify standardization needs.

This script scans Python files in the specified directory and checks docstrings for
compliance with the Google docstring style guide. It identifies functions, methods,
and classes that need docstring improvements.
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional


class DocstringInfo(NamedTuple):
    """Information about a docstring."""

    name: str
    lineno: int
    has_docstring: bool
    has_args_section: bool
    has_returns_section: bool
    has_raises_section: bool
    needs_raises: bool
    docstring: Optional[str] = None


def extract_docstring(node: ast.AST) -> Optional[str]:
    """Extract the docstring from an AST node.

    Args:
        node: AST node to extract docstring from

    Returns:
        The docstring if it exists, None otherwise
    """
    if isinstance(
        node, (ast.AsyncFunctionDef, ast.FunctionDef, ast.ClassDef, ast.Module)
    ):
        docstring = ast.get_docstring(node)
        return docstring
    return None


def has_section(docstring: str, section_name: str) -> bool:
    """Check if a docstring contains a specific section.

    Args:
        docstring: The docstring to check
        section_name: The section name to look for

    Returns:
        True if the section exists, False otherwise
    """
    if not docstring:
        return False

    # Handle different section styles
    patterns = [
        rf"{section_name}:",  # Standard Google style
        rf"{section_name}\s*:",  # Allow space before colon
        rf"{section_name}$",  # Section name at end of line
    ]

    for pattern in patterns:
        if re.search(pattern, docstring, re.MULTILINE | re.IGNORECASE):
            return True

    return False


def check_raises_needed(node: ast.AST) -> bool:
    """Check if a node likely needs a Raises section based on code content.

    Args:
        node: AST node to check

    Returns:
        True if the node likely needs a Raises section, False otherwise
    """

    class RaiseVisitor(ast.NodeVisitor):
        def __init__(self):
            self.has_raise = False

        def visit_Raise(self, node):
            self.has_raise = True

        def visit_Try(self, node):
            # Visit try block
            for stmt in node.body:
                self.visit(stmt)

            # Visit except blocks
            for handler in node.handlers:
                if handler.body:
                    for stmt in handler.body:
                        # Check if there's a raise in the except block
                        if isinstance(stmt, ast.Raise):
                            self.has_raise = True
                        self.visit(stmt)

    visitor = RaiseVisitor()
    visitor.visit(node)
    return visitor.has_raise


def analyze_file(file_path: Path) -> List[DocstringInfo]:
    """Analyze docstrings in a Python file.

    Args:
        file_path: Path to the Python file

    Returns:
        List of DocstringInfo objects with analysis results
    """
    with open(file_path, "r", encoding="utf-8") as f:
        file_content = f.read()

    try:
        tree = ast.parse(file_content, filename=str(file_path))
    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
        return []

    results = []

    # Check module docstring
    module_docstring = ast.get_docstring(tree)
    if module_docstring:
        results.append(
            DocstringInfo(
                name=file_path.stem,
                lineno=1,
                has_docstring=True,
                has_args_section=False,  # Module doesn't need Args
                has_returns_section=False,  # Module doesn't need Returns
                has_raises_section=False,  # Module doesn't need Raises
                needs_raises=False,
                docstring=module_docstring,
            )
        )
    else:
        results.append(
            DocstringInfo(
                name=file_path.stem,
                lineno=1,
                has_docstring=False,
                has_args_section=False,
                has_returns_section=False,
                has_raises_section=False,
                needs_raises=False,
                docstring=None,
            )
        )

    # Visit all nodes
    for node in ast.walk(tree):
        # Check functions and methods
        if isinstance(node, ast.FunctionDef):
            docstring = extract_docstring(node)
            needs_raises = check_raises_needed(node)

            results.append(
                DocstringInfo(
                    name=node.name,
                    lineno=node.lineno,
                    has_docstring=docstring is not None,
                    has_args_section=has_section(docstring, "Args")
                    if docstring
                    else False,
                    has_returns_section=has_section(docstring, "Returns")
                    if docstring
                    else False,
                    has_raises_section=has_section(docstring, "Raises")
                    if docstring
                    else False,
                    needs_raises=needs_raises,
                    docstring=docstring,
                )
            )

        # Check classes
        elif isinstance(node, ast.ClassDef):
            docstring = extract_docstring(node)

            results.append(
                DocstringInfo(
                    name=node.name,
                    lineno=node.lineno,
                    has_docstring=docstring is not None,
                    has_args_section=False,  # Classes usually don't need Args
                    has_returns_section=False,  # Classes don't need Returns
                    has_raises_section=False,  # Classes might need Raises but hard to detect
                    needs_raises=False,
                    docstring=docstring,
                )
            )

    return results


def analyze_directory(
    directory: Path, exclude_dirs: List[str] = None
) -> Dict[Path, List[DocstringInfo]]:
    """Analyze all Python files in a directory.

    Args:
        directory: Path to the directory
        exclude_dirs: List of directory names to exclude

    Returns:
        Dictionary mapping file paths to their analysis results
    """
    if exclude_dirs is None:
        exclude_dirs = ["__pycache__", ".git", ".github", "venv", ".venv", "env"]

    results = {}

    for root, dirs, files in os.walk(directory):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in (exclude_dirs or [])]

        for file in files:
            if file.endswith(".py"):
                file_path = Path(root) / file
                file_results = analyze_file(file_path)

                if file_results:
                    results[file_path] = file_results

    return results


def format_results(
    results: Dict[Path, List[DocstringInfo]], show_all: bool = False
) -> str:
    """Format analysis results into a readable report.

    Args:
        results: Dictionary mapping file paths to their analysis results
        show_all: Whether to show all results or only problematic ones

    Returns:
        Formatted report as a string
    """
    report_lines = []
    file_count = 0
    problem_count = 0

    for file_path, file_results in sorted(results.items()):
        file_problems = False
        file_lines = []

        for result in file_results:
            problems = []

            if not result.has_docstring:
                problems.append("Missing docstring")
            elif len(result.name) > 1:  # Skip module docstring here
                if result.name.startswith("__") and result.name.endswith("__"):
                    # Special methods like __init__ don't always need all sections
                    continue

                # For normal functions
                if not result.has_args_section and not result.name.startswith("_"):
                    if "test_" not in result.name:  # Skip test functions
                        problems.append("Missing Args section")

                if not result.has_returns_section:
                    problems.append("Missing Returns section")

                if result.needs_raises and not result.has_raises_section:
                    problems.append("Missing Raises section")

                # Check for incorrect format
                if result.docstring and "param" in result.docstring.lower():
                    problems.append("Using :param: instead of Args")
                if result.docstring and "return:" in result.docstring.lower():
                    problems.append("Using :return: instead of Returns")

            if problems or show_all:
                file_lines.append(
                    f"  Line {result.lineno}: {result.name}: {', '.join(problems) if problems else 'OK'}"
                )

            if problems:
                file_problems = True
                problem_count += 1

        if file_problems or show_all:
            # Display the path without trying to make it relative
            file_lines.insert(0, f"\n{file_path}:")
            report_lines.extend(file_lines)
            file_count += 1

    # Add summary
    total_files = len(results)
    report_lines.append("\nSummary:")
    report_lines.append(f"- Analyzed {total_files} Python files")
    report_lines.append(f"- Found {file_count} files with docstring issues")
    report_lines.append(f"- Found {problem_count} total docstring issues")

    return "\n".join(report_lines)


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description="Analyze docstrings in Python files")
    parser.add_argument("path", help="Path to directory to analyze")
    parser.add_argument(
        "--all", action="store_true", help="Show all results, not just problems"
    )
    parser.add_argument(
        "--exclude", nargs="+", default=[], help="Additional directories to exclude"
    )
    args = parser.parse_args()

    directory = Path(args.path)
    if not directory.exists() or not directory.is_dir():
        print(f"Error: {args.path} is not a valid directory")
        return 1

    exclude_dirs = [
        "__pycache__",
        ".git",
        ".github",
        "venv",
        ".venv",
        "env",
    ] + args.exclude
    results = analyze_directory(directory, exclude_dirs)
    report = format_results(results, args.all)

    print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
