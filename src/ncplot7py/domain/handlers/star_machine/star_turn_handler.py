from __future__ import annotations

from typing import Optional, Tuple, List

from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.handlers.star_machine.automatic_coordinate_handler import StarAutomaticCoordinateHandler
from ncplot7py.domain.handlers.star_machine.g266_handler import StarG266Handler
from ncplot7py.domain.handlers.star_machine.spindle_fluctuation_handler import StarSpindleFluctuationHandler


class StarTurnHandler(Handler):
    """Compatibility facade for the former monolithic Star handler."""

    def __init__(self, next_handler: Optional[Handler] = None):
        super().__init__(next_handler=next_handler)
        self._chain = StarSpindleFluctuationHandler(
            next_handler=StarAutomaticCoordinateHandler(
                next_handler=StarG266Handler(next_handler=next_handler)
            )
        )

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[List], Optional[float]]:
        if any(str(code).strip().upper() == "G300" for code in node.g_code):
            return super().handle(node, state)
        return self._chain.handle(node, state)


__all__ = ["StarTurnHandler"]
