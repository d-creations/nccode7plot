import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenCanal
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestFanucTurnDrillingCycles(unittest.TestCase):
    def _canal(self, axes=None):
        state = CNCState(
            axes=axes or {"X": 10.0, "Y": 0.0, "Z": 0.0, "C": 0.0},
            machine_config=get_machine_config("FANUC_TURN"),
        )
        state.spindle_speed = 1000.0
        return state, UniversalConfigDrivenCanal("C1", init_state=state)

    @staticmethod
    def _all_points(canal):
        return [point for points, _duration in canal.get_tool_path() for point in points]

    @staticmethod
    def _total_duration(canal):
        return sum(duration for _points, duration in canal.get_tool_path())

    def test_g83_pecks_and_g98_returns_to_initial_level(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G83", "G98"},
                command_parameter={"Z": "-10", "R": "-2", "Q": "3000", "F": "100"},
            )
        ])

        points = self._all_points(canal)
        duration = self._total_duration(canal)
        self.assertAlmostEqual(min(point.z for point in points), -12.0)
        self.assertAlmostEqual(state.get_axis("Z"), 0.0)
        self.assertGreater(duration, 0.0)
        self.assertEqual(state.get_modal("drilling_cycle"), "G83")

    def test_g83_is_modal_and_g80_clears_cycle_data(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G83", "G99"},
                command_parameter={"Z": "-5", "R": "-1", "F": "100"},
            ),
            NCCommandNode(command_parameter={"C": "90"}),
            NCCommandNode(g_code_command={"G80"}),
        ])

        self.assertGreater(len(canal.get_tool_path()), 2)
        self.assertAlmostEqual(state.get_axis("C"), 90.0)
        self.assertAlmostEqual(state.get_axis("Z"), -1.0)
        self.assertIsNone(state.get_modal("drilling_cycle"))
        self.assertNotIn("fanuc_turn_drilling_cycle", state.extra)

    def test_g84_taps_to_depth_and_reverses_out(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G84", "G98"},
                command_parameter={"Z": "-8", "R": "-2", "F": "1"},
            )
        ])

        points = self._all_points(canal)
        self.assertAlmostEqual(min(point.z for point in points), -10.0)
        self.assertAlmostEqual(state.get_axis("Z"), 0.0)
        self.assertTrue(state.extra["fanuc_turn.last_tapping_reversal"])

    def test_g85_bores_and_returns_from_bottom(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G85", "G99"},
                command_parameter={"Z": "-6", "R": "-1", "F": "100"},
            )
        ])

        points = self._all_points(canal)
        duration = self._total_duration(canal)
        self.assertAlmostEqual(min(point.z for point in points), -7.0)
        self.assertAlmostEqual(state.get_axis("Z"), -1.0)
        self.assertGreater(duration, 0.0)

    def test_g87_side_drills_on_x_axis(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G87", "G98"},
                command_parameter={"Z": "20", "X": "-10", "R": "-2", "F": "100"},
            )
        ])

        points = self._all_points(canal)
        self.assertAlmostEqual(min(point.x for point in points), 3.0)
        self.assertAlmostEqual(state.get_axis("X"), 10.0)
        self.assertAlmostEqual(state.get_axis("Z"), 20.0)

    def test_g89_side_boring_uses_x_axis(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G89", "G99"},
                command_parameter={"X": "-8", "R": "-1", "F": "100"},
            )
        ])

        points = self._all_points(canal)
        self.assertAlmostEqual(min(point.x for point in points), 5.0)
        self.assertAlmostEqual(state.get_axis("X"), 9.0)

    def test_cycle_primitives_keep_drawing_semantics(self):
        _state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G83", "G98"},
                command_parameter={"Z": "-4", "R": "-1", "Q": "2000", "F": "100"},
                nc_code_line_nr=12,
            )
        ])

        motion_nodes = canal.get_exec_nodes()
        self.assertEqual(len(motion_nodes), len(canal.get_tool_path()))
        self.assertEqual({node.motion_geometry for node in motion_nodes}, {"LINEAR"})
        self.assertEqual({node.motion_traversal for node in motion_nodes}, {"RAPID", "FEED"})
        self.assertEqual(
            {node.motion_source_code for node in motion_nodes},
            {"G00", "G01"},
        )
        self.assertEqual({node.nc_code_line_nr for node in motion_nodes}, {12})


if __name__ == "__main__":
    unittest.main()