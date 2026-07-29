"""Fanuc source lexer."""
from __future__ import annotations

import re
from typing import List

from ncplot7py.interfaces.BaseNCProgramLexer import BaseNCProgramLexer, NCSourceStatement


class FanucProgramLexer(BaseNCProgramLexer):
    """Handle nested parenthesis comments and legacy semicolon statements."""

    def lex(self, program: str) -> List[NCSourceStatement]:
        if program is None:
            return []

        statements: List[NCSourceStatement] = []
        for line_number, physical_line in enumerate(program.splitlines(), start=1):
            statements.extend(self._lex_line(physical_line, line_number))

        if not statements and program:
            statements.extend(self._lex_line(program, 1))
        return statements

    def _lex_line(self, line: str, line_number: int) -> List[NCSourceStatement]:
        statements: List[NCSourceStatement] = []
        current: List[str] = []
        depth = 0
        in_string = False
        statement_column = 1
        preserve_parentheses = re.search(r"#\s*3000\s*=", line, re.IGNORECASE) is not None

        for index, character in enumerate(line):
            if character == '"' and depth == 0:
                in_string = not in_string
                current.append(character)
            elif not in_string and character == '(':
                depth += 1
                if preserve_parentheses:
                    current.append(character)
            elif not in_string and character == ')' and depth:
                depth -= 1
                if preserve_parentheses:
                    current.append(character)
            elif not in_string and depth == 0 and character == ';':
                statements.append(NCSourceStatement("".join(current), line_number, statement_column))
                current = []
                statement_column = index + 2
            elif depth == 0 or preserve_parentheses:
                current.append(character)

        statements.append(NCSourceStatement("".join(current), line_number, statement_column))
        return statements

    def strip_comments(self, line: str) -> str:
        """Remove nested comments without treating parentheses in strings as comments."""
        if not line or '(' not in line:
            return line

        result: List[str] = []
        depth = 0
        in_string = False
        for character in line:
            if character == '"' and depth == 0:
                in_string = not in_string
                result.append(character)
            elif not in_string and character == '(':
                depth += 1
            elif not in_string and character == ')' and depth:
                depth -= 1
            elif depth == 0:
                result.append(character)
        return "".join(result)
