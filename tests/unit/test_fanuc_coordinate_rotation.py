import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionNode
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenCanal
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestFanucCoordinateRotation(unittest.TestCase):
    def _canal(self, machine="FANUC_TURN"):
        state = CNCState(machine_config=get_machine_config(machine))
        return state, UniversalConfigDrivenCanal("C1", init_state=state)

    def test_g68_1_rotates_g18_program_coordinates(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G68.1"}, command_parameter={"X": "0", "Z": "0", "R": "90.0"}),
            NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "0", "Z": "10", "F": "100"}, nc_code_line_nr=2),
        ])

        self.assertAlmostEqual(state.get_axis("Z"), 0.0, places=7)
        self.assertAlmostEqual(state.get_axis("X"), 10.0, places=7)
        node = canal.get_exec_nodes()[0]
        self.assertEqual(node.motion_geometry, "LINEAR")
        self.assertEqual(node.motion_traversal, "FEED")
        self.assertEqual(node.motion_source_code, "G01")
        self.assertEqual(node.nc_code_line_nr, 2)

    def test_g69_1_cancels_rotation(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G68.1"}, command_parameter={"R": "90.0"}),
            NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "0", "Z": "10", "F": "100"}),
            NCCommandNode(g_code_command={"G69.1"}),
            NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "0", "Z": "5"}),
        ])

        self.assertAlmostEqual(state.get_axis("X"), 0.0, places=7)
        self.assertAlmostEqual(state.get_axis("Z"), 5.0, places=7)
        self.assertNotIn("fanuc.coordinate_rotation", state.extra)

    def test_star_g69_alias_cancels_rotation(self):
        state, canal = self._canal("FANUC_STAR_x-D_y-R_z_R")
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G68.1"}, command_parameter={"R": "45.0"}),
            NCCommandNode(g_code_command={"G69"}),
        ])
        self.assertNotIn("fanuc.coordinate_rotation", state.extra)

    def test_first_move_after_g68_1_must_be_absolute(self):
        _state, canal = self._canal()
        with self.assertRaises(ExceptionNode) as error:
            canal.run_nc_code_list([
                NCCommandNode(g_code_command={"G68.1"}, command_parameter={"R": "45.0"}),
                NCCommandNode(g_code_command={"G1"}, command_parameter={"W": "10", "F": "100"}),
            ])
        self.assertEqual(error.exception.code, 682)

    def test_g68_1_supports_implied_thousandth_degree_angle(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G68.1"}, command_parameter={"R": "45000"}),
        ])
        self.assertEqual(state.extra["fanuc.coordinate_rotation"]["angle"], 45.0)

    def test_g68_1_rejects_canned_cycle_while_active(self):
        _state, canal = self._canal()
        with self.assertRaises(ExceptionNode) as error:
            canal.run_nc_code_list([
                NCCommandNode(g_code_command={"G68.1"}, command_parameter={"R": "45.0"}),
                NCCommandNode(g_code_command={"G83"}, command_parameter={"Z": "-5", "R": "-1", "F": "100"}),
            ])
        self.assertEqual(error.exception.code, 687)


if __name__ == "__main__":
    unittest.main()