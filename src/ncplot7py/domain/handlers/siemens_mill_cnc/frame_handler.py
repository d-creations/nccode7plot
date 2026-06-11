"""Siemens frame command handling."""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.handlers.siemens_mill_cnc.common import ensure_siemens_scope
from ncplot7py.domain.handlers.siemens_mill_cnc.variable_handler import SiemensExpressionEvaluator


class SiemensFrameHandler(Handler):
    def __init__(self, next_handler: Optional[Handler] = None):
        super().__init__(next_handler=next_handler)
        self._evaluator = SiemensExpressionEvaluator()

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        command = (node.variable_command or "").strip()
        if "$P_UIFR" in command.upper() and "=" in command:
            self._handle_uifr_assignment(command, state)
        elif re.match(r"^(TRANS|ATRANS|ROT|AROT)\b", command, re.IGNORECASE):
            self._handle_programmed_frame(command, state)
        return super().handle(node, state)

    def _handle_uifr_assignment(self, command: str, state: CNCState) -> None:
        scope = ensure_siemens_scope(state)
        left, right = command.split("=", 1)
        index_match = re.search(r"\[([^\]]+)\]", left)
        if not index_match:
            return
        index = int(float(self._evaluator.evaluate(index_match.group(1), state)))
        frame = {"translation": {}, "rotation": {}}
        for part in right.split(":"):
            part = part.strip()
            func_match = re.match(r"^(C?A?TRANS|C?A?ROT)\s*\((.*)\)$", part, re.IGNORECASE)
            if not func_match:
                continue
            func_name = func_match.group(1).upper()
            pairs = self._parse_axis_pairs(func_match.group(2), state)
            if "TRANS" in func_name:
                frame["translation"].update(pairs)
            elif "ROT" in func_name:
                frame["rotation"].update(pairs)
        scope["frames"][index] = frame

    def _handle_programmed_frame(self, command: str, state: CNCState) -> None:
        scope = ensure_siemens_scope(state)
        match = re.match(r"^(A?TRANS|A?ROT)\s*(?:\((.*)\)|(.*))$", command, re.IGNORECASE)
        if not match:
            return
        name = match.group(1).upper()
        args = match.group(2) or match.group(3) or ""
        key = "translation" if "TRANS" in name else "rotation"
        scope.setdefault("active_frame", {}).setdefault(key, {}).update(self._parse_axis_pairs(args, state))

    def _parse_axis_pairs(self, text: str, state: CNCState) -> Dict[str, float]:
        tokens = [token.strip() for token in text.split(",") if token.strip()]
        result: Dict[str, float] = {}
        index = 0
        while index + 1 < len(tokens):
            axis = tokens[index].strip().upper()
            if axis in {"X", "Y", "Z", "A", "B", "C"}:
                result[axis] = self._evaluator.evaluate(tokens[index + 1], state)
            index += 2
        return result


__all__ = ["SiemensFrameHandler"]