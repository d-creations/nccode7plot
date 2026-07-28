"""Registry and factory for NC program lexers."""
from __future__ import annotations

from typing import Dict, Optional, Type

from ncplot7py.interfaces.BaseNCProgramLexer import BaseNCProgramLexer
from ncplot7py.infrastructure.lexers.fanuc_program_lexer import FanucProgramLexer
from ncplot7py.infrastructure.lexers.siemens_program_lexer import SiemensProgramLexer


_LEXER_REGISTRY: Dict[str, Type[BaseNCProgramLexer]] = {
    "fanuc": FanucProgramLexer,
    "siemens": SiemensProgramLexer,
}


def register_program_lexer(name: str, lexer_class: Type[BaseNCProgramLexer]) -> None:
    """Register a lexer implementation for a machine configuration identifier."""
    _LEXER_REGISTRY[name.lower()] = lexer_class


def create_program_lexer(name: Optional[str]) -> BaseNCProgramLexer:
    """Create the configured lexer, retaining Fanuc as the legacy default."""
    normalized = (name or "fanuc").lower()
    if normalized == "auto":
        normalized = "fanuc"
    lexer_class = _LEXER_REGISTRY.get(normalized)
    if lexer_class is None:
        raise ValueError(f"Unknown NC program lexer: {name}")
    return lexer_class()
