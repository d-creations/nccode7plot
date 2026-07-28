"""Parser interface for mapping NC/G-code text to `BaseNCCommandNode`.

This small interface defines a parser contract so different parser
implementations can be swapped in tests or at runtime.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from .BaseNCCommandNode import BaseNCCommandNode


class BaseNCCommandParser(ABC):
    """Abstract parser that converts an NC command string into a node.

    Implementations must return an object implementing
    :class:`BaseNCCommandNode`.
    """

    @abstractmethod
    def parse(self, nc_command_string: str, line_nr: Optional[int] = None) -> BaseNCCommandNode:
        """Parse a single line of NC/G-code and return a node representation.

        Parameters:
            nc_command_string: The raw NC text line to parse.
            line_nr: Optional 1-based source line number to attach to the node.

        Returns:
            An instance implementing :class:`BaseNCCommandNode`.
        """
        raise NotImplementedError()

    def split_program(self, program: str) -> List[Tuple[str, int]]:
        """Split source text into commands while preserving source line numbers.

        The default keeps the legacy semicolon-separated transport format used
        by Fanuc callers. Dialects where semicolon has another meaning override
        this method.
        """
        if program is None:
            return []
        commands: List[Tuple[str, int]] = []
        for line_number, physical_line in enumerate(program.splitlines(), start=1):
            commands.extend((command, line_number) for command in physical_line.split(";"))
        if not commands and program:
            commands.append((program, 1))
        return commands
