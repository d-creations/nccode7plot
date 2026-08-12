"""FANUC turning input-unit handling for G20 and G21."""
from __future__ import annotations

from typing import List, Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionTyps, raise_nc_error
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode


class FanucTurnUnitHandler(Handler):
    """Select program input units and normalize new linear words to millimeters."""

    LINEAR_WORDS = {"X", "Y", "Z", "U", "V", "W", "I", "J", "K", "R", "F"}

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[List], Optional[float]]:
        codes = {str(code).strip().upper() for code in node.g_code}
        has_g20 = bool(codes & {"G20", "G020"})
        has_g21 = bool(codes & {"G21", "G021"})

        if has_g20 and has_g21:
            raise_nc_error(
                ExceptionTyps.NCCodeErrors,
                140,
                message="Conflicting input unit codes G20 and G21",
                value=str(node.g_code),
                line=node.nc_code_line_nr or 0,
            )

        if has_g20:
            state.set_modal("units", "G20")
        elif has_g21:
            state.set_modal("units", "G21")

        if state.get_modal("units") == "G20":
            linear_words = set(self.LINEAR_WORDS)
            if any(str(code).strip().upper() == "G68.1" for code in node.g_code):
                linear_words.discard("R")
            for word in linear_words.intersection(node.command_parameter):
                try:
                    node.command_parameter[word] = str(float(node.command_parameter[word]) * 25.4)
                except (TypeError, ValueError):
                    continue

        return super().handle(node, state)


__all__ = ["FanucTurnUnitHandler"]