"""Siemens path mode handling."""
from __future__ import annotations

from typing import Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.handlers.siemens_mill_cnc.common import ensure_siemens_scope


class SiemensPathModeHandler(Handler):
    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        scope = ensure_siemens_scope(state)
        command = (node.variable_command or "").strip().upper()
        if command in {"COMPON", "COMPCURV", "COMPCAD", "COMPOF"}:
            scope["path_mode"] = command
        for g_code in node.g_code:
            code = str(g_code).upper()
            if code in {"G64", "G641", "G642", "G643", "G644", "G645"}:
                scope["path_mode"] = code
        return super().handle(node, state)


__all__ = ["SiemensPathModeHandler"]