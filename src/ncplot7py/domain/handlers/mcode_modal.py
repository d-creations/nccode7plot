"""Shared mechanics for machine-specific modal M-code handlers."""
from __future__ import annotations

from typing import List, Optional, Set, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode


class BaseModalMCodeHandler(Handler):
    """Apply standard modal M-code state and optional profile actions."""

    c_axis_reset_codes: Set[str] = set()

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[List], Optional[float]]:
        m_code = self._normalize_m_code(node.command_parameter.get("M"))
        if m_code in {"M3", "M4", "M5"}:
            state.set_modal("spindle_direction", m_code)
        elif m_code in {"M7", "M8", "M9"}:
            state.set_modal("coolant_mode", m_code)

        self._apply_machine_specific_state(m_code, state)

        if m_code in self.c_axis_reset_codes:
            return self._return_c_axis_to_zero(node, state)
        return super().handle(node, state)

    def _apply_machine_specific_state(self, m_code: Optional[str], state: CNCState) -> None:
        pass

    def _return_c_axis_to_zero(
        self, node: NCCommandNode, state: CNCState
    ) -> Tuple[Optional[List], Optional[float]]:
        reset_node = NCCommandNode(
            g_code_command={"G0"},
            command_parameter={"C": "0"},
            nc_code_line_nr=node.nc_code_line_nr,
        )
        if self.next_handler is None:
            state.set_axis("C", 0.0)
            return None, None
        return self.next_handler.handle(reset_node, state)

    @staticmethod
    def _normalize_m_code(value: object) -> Optional[str]:
        text = str(value or "").strip().upper()
        if text.startswith("M"):
            text = text[1:]
        try:
            return f"M{int(text)}"
        except (TypeError, ValueError):
            return None


__all__ = ["BaseModalMCodeHandler"]