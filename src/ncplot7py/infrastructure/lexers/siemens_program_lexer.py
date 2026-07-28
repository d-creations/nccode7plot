"""Siemens source lexer."""
from __future__ import annotations

import re
from typing import List

from ncplot7py.interfaces.BaseNCProgramLexer import BaseNCProgramLexer, NCSourceStatement


class SiemensProgramLexer(BaseNCProgramLexer):
    """Handle Siemens semicolon comments while preserving physical lines."""

    _SETAL_PATTERN = re.compile(r"^\s*SETAL\s*\(", re.IGNORECASE)

    def lex(self, program: str) -> List[NCSourceStatement]:
        if program is None:
            return []

        statements: List[NCSourceStatement] = []
        for line_number, physical_line in enumerate(program.splitlines(), start=1):
            statements.append(
                NCSourceStatement(self.strip_comments(physical_line), line_number)
            )

        if not statements and program:
            statements.append(NCSourceStatement(self.strip_comments(program), 1))
        return statements

    def strip_comments(self, line: str) -> str:
        if not line or ';' not in line or self._SETAL_PATTERN.match(line):
            return line

        in_string = False
        for index, character in enumerate(line):
            if character == '"':
                in_string = not in_string
            elif character == ';' and not in_string:
                return line[:index]
        return line
