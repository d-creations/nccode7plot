import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionNode
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenCanal
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestStarB1Tilting(unittest.TestCase):
    def _canal(self, path=1):
        state = CNCState(machine_config=get_machine_config("FANUC_STAR_x-D_y-R_z_R"))
        state.extra["current_tool_code"] = 1600
        return state, UniversalConfigDrivenCanal(f"C{path}", init_state=state)

    def test_g910_indexes_b_and_returns_drawing_metadata(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G910"},
                command_parameter={"B": "45", "X": "20", "Z": "5"},
                nc_code_line_nr=10,
            )
        ])

        self.assertAlmostEqual(state.get_axis("B"), 45.0)
        setup = state.extra["star.b1_tilting"]
        self.assertEqual(setup["mode"], "G910")
        self.assertEqual(setup["coordinate_reference"], {"X": 10.0, "Z": 5.0})
        self.assertFalse(setup["automatic_offset_calculated"])
        node = canal.get_exec_nodes()[0]
        self.assertEqual(node.motion_geometry, "LINEAR")
        self.assertEqual(node.motion_traversal, "RAPID")
        self.assertEqual(node.motion_source_code, "G910")
        self.assertEqual(node.nc_code_line_nr, 10)

    def test_g920_uses_separate_mode(self):
        state, canal = self._canal()
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G920"}, command_parameter={"B": "-30"})
        ])
        self.assertEqual(state.get_modal("star_b1_tilting"), "G920")
        self.assertAlmostEqual(state.get_axis("B"), -30.0)

    def test_g910_requires_t1600_to_t1900(self):
        state, canal = self._canal()
        state.extra["current_tool_code"] = 1500
        with self.assertRaises(ExceptionNode) as error:
            canal.run_nc_code_list([
                NCCommandNode(g_code_command={"G910"}, command_parameter={"B": "45"})
            ])
        self.assertEqual(error.exception.code, 3233)

    def test_g910_rejects_wrong_path_mode(self):
        state, canal = self._canal(path=1)
        state.extra["star.path_mode"] = "M172"
        with self.assertRaises(ExceptionNode) as error:
            canal.run_nc_code_list([
                NCCommandNode(g_code_command={"G910"}, command_parameter={"B": "45"})
            ])
        self.assertEqual(error.exception.code, 3235)


if __name__ == "__main__":
    unittest.main()