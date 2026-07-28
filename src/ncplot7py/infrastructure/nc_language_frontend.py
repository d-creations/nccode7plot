"""Composition of machine-specific source lexing and command parsing."""
from __future__ import annotations

from dataclasses import dataclass

from ncplot7py.interfaces.BaseNCCommandParser import BaseNCCommandParser
from ncplot7py.interfaces.BaseNCProgramLexer import BaseNCProgramLexer
from ncplot7py.infrastructure.lexers import create_program_lexer
from ncplot7py.infrastructure.parsers.nc_command_parser import NCCommandStringParser


@dataclass(frozen=True)
class NCLanguageFrontend:
    """The source-language components selected for one machine configuration."""

    lexer: BaseNCProgramLexer
    parser: BaseNCCommandParser


def create_language_frontend(machine_config) -> NCLanguageFrontend:
    """Build a frontend from declarative machine configuration identifiers."""
    parser_name = getattr(machine_config, "parser_name", None)
    lexer_name = getattr(machine_config, "lexer_name", None) or parser_name
    return NCLanguageFrontend(
        lexer=create_program_lexer(lexer_name),
        parser=NCCommandStringParser(parser_name=parser_name),
    )
