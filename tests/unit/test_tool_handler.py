import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.handlers.star_machine.tool_handler import StarFanucToolHandler
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestToolHandler(unittest.TestCase):
    def test_star_t0400_uses_tool_four(self):
        state = CNCState(machine_config=get_machine_config("FANUC_STAR_x-D_y-D_z_R.M.S"))

        StarFanucToolHandler().handle(NCCommandNode(command_parameter={"T": "0400"}), state)

        self.assertEqual(state.extra["current_tool_number"], 4)
        self.assertEqual(state.extra["current_tool_code"], 400)

    def test_star_t400_is_interpreted_as_tool_four_with_offset_zero(self):
        state = CNCState(machine_config=get_machine_config("FANUC_STAR_x-D_y-D_z_R.M.S"))

        StarFanucToolHandler().handle(NCCommandNode(command_parameter={"T": "400"}), state)

        self.assertEqual(state.extra["current_tool_number"], 4)


if __name__ == "__main__":
    unittest.main()