"""Siemens transformation command handling."""
from __future__ import annotations

from typing import Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.handlers.siemens_mill_cnc.common import ensure_siemens_scope


class SiemensTransformationHandler(Handler):
    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        scope = ensure_siemens_scope(state)
        command = (node.variable_command or "").strip().upper()
        if command.startswith("TRAORI"):
            scope["transformations"].setdefault("TRAORI", {})["active"] = True
        elif command.startswith("TRAFOOF"):
            scope["transformations"].setdefault("TRAORI", {})["active"] = False
        return super().handle(node, state)


__all__ = ["SiemensTransformationHandler"]