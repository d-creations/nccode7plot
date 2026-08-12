"""Tool-change handler for standard Fanuc controls."""
from __future__ import annotations

from typing import List, Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.domain.handlers.base_tool_handler import BaseToolHandler
from ncplot7py.shared.nc_nodes import NCCommandNode


class FanucToolHandler(BaseToolHandler, Handler):
    """Handle tool changes for standard Fanuc controls."""

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[List], Optional[float]]:
        self._handle_tool_change(node, state)
        if self.next_handler is not None:
            return self.next_handler.handle(node, state)
        return None, None