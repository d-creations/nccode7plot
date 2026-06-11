"""Siemens built-in command markers used by plotting."""
from __future__ import annotations

import re
from typing import Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.handlers.siemens_mill_cnc.common import ensure_siemens_scope
from ncplot7py.domain.handlers.siemens_mill_cnc.variable_handler import SiemensExpressionEvaluator


class SiemensBuiltinHandler(Handler):
    def __init__(self, next_handler: Optional[Handler] = None):
        super().__init__(next_handler=next_handler)
        self._evaluator = SiemensExpressionEvaluator()

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        scope = ensure_siemens_scope(state)
        command = (node.variable_command or "").strip()
        upper = command.upper()

        setal_match = re.match(r"^SETAL\s*\(\s*([^\)]+)\s*\)(?:\s*;\s*(.*))?$", command, re.IGNORECASE)
        if setal_match:
            code = int(float(self._evaluator.evaluate(setal_match.group(1), state)))
            message = setal_match.group(2) or "failure to reach the touch point" if code == 62111 else ""
            state.extra.setdefault("alarms", []).append({"code": code, "message": message, "line": node.nc_code_line_nr})
        elif re.match(r"^SPOSA?\s*=", command, re.IGNORECASE):
            _, value = command.split("=", 1)
            scope["spindle_position"] = self._evaluator.evaluate(value, state)
        elif upper == "RET" or upper == "M17":
            state.extra["program_returned"] = True
        elif upper == "STOPRE":
            scope["preprocess_stops"].append(node.nc_code_line_nr)
        elif upper.startswith("MSG"):
            state.extra.setdefault("messages", []).append({"message": command, "line": node.nc_code_line_nr})
        if str(node.command_parameter.get("M", "")) == "82":
            scope["probe_enabled"] = True
        elif str(node.command_parameter.get("M", "")) == "83":
            scope["probe_enabled"] = False
        return super().handle(node, state)


__all__ = ["SiemensBuiltinHandler"]