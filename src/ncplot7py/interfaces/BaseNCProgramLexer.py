"""Contract for machine-specific NC source lexers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class NCSourceStatement:
    """One executable source statement and its original location."""

    text: str
    line: int
    column: int = 1


class BaseNCProgramLexer(ABC):
    """Convert machine-specific source text into parser-ready statements."""

    @abstractmethod
    def lex(self, program: str) -> List[NCSourceStatement]:
        """Return parser-ready statements with original source locations."""
        raise NotImplementedError()

    @abstractmethod
    def strip_comments(self, line: str) -> str:
        """Remove comments from one source line according to the dialect."""
        raise NotImplementedError()
