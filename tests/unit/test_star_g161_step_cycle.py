import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionNode
from ncplot7py.domain.handlers.fanuc_turn_cnc.gcode_group2_speed_mode import SpeedMode
from ncplot7py.domain.handlers.fanuc_turn_cnc.gcode_group5_feed_mode import FeedMode
from ncplot7py.domain.handlers.star_machine.g161_step_cycle_handler import StarG161StepCycleHandler
from ncplot7py.domain.machines import MachineConfig, get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenCanal
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestStarG161StepCycle(unittest.TestCase):
    def _state(self):
        state = CNCState(machine_config=get_machine_config("FANUC_STAR_x-D_y-R_z_R"))
        state.extra["surface_speed_mode"] = SpeedMode.CONSTANT_REV
        state.extra["feed_mode"] = FeedMode.FEED_PER_REV
        state.spindle_speed = 1000.0
        return state

    def test_g161_stores_typed_cycle_parameters(self):
        state = self._state()
        canal = UniversalConfigDrivenCanal("C1", init_state=state)
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G161"},
                command_parameter={"X": "10", "Y": "5", "Z": "-20", "A": "1.5", "F": "0.1", "D": "2", "Q": "3"},
            )
        ])

        self.assertEqual(
            state.extra["star.g161"]["parameters"],
            {"a": 1.5, "f": 0.1, "d": 2.0, "q": 3.0},
        )
        self.assertTrue(state.extra["star.g161"]["geometry_available"])
        self.assertEqual(
            state.extra["star.g161"]["geometry_source"],
            "linear_endpoint_approximation",
        )
        self.assertFalse(state.extra["star.g161"]["physical_cycle_path_available"])
        self.assertEqual(state.get_modal("star_step_cycle"), "G161")
        self.assertEqual(len(canal.get_tool_path()), 1)
        points, duration = canal.get_tool_path()[0]
        self.assertGreater(len(points), 1)
        self.assertEqual((points[-1].x, points[-1].y, points[-1].z), (5.0, 5.0, -20.0))
        self.assertAlmostEqual(duration, 12.7279220614)
        motion_node = canal.get_exec_nodes()[0]
        self.assertEqual(motion_node.motion_geometry, "LINEAR")
        self.assertEqual(motion_node.motion_traversal, "FEED")
        self.assertEqual(motion_node.motion_source_code, "G161")

    def test_configured_chain_accepts_g161_without_m41(self):
        state = CNCState(machine_config=get_machine_config("FANUC_STAR_x-D_y-R_z_R"))
        canal = UniversalConfigDrivenCanal("C1", init_state=state)
        canal.run_nc_code_list([
            NCCommandNode(g_code_command={"G97", "G99"}, command_parameter={"S": "1000"}),
            NCCommandNode(
                g_code_command={"G161"},
                command_parameter={"Z": "-10", "A": "1", "F": "0.1", "D": "2", "Q": "3"},
            ),
        ])

        self.assertNotIn("star.machining_mode", state.extra)
        self.assertEqual(state.extra["star.g161"]["parameters"]["q"], 3.0)

    def test_g161_accepts_only_a_and_d_without_q_or_m41(self):
        state = self._state()
        state.spindle_speed = 0.0
        canal = UniversalConfigDrivenCanal("C1", init_state=state)
        canal.run_nc_code_list([
            NCCommandNode(
                g_code_command={"G161"},
                command_parameter={"A": "1.5", "D": "2"},
            ),
        ])

        self.assertEqual(
            state.extra["star.g161"]["parameters"],
            {"a": 1.5, "f": None, "d": 2.0, "q": None},
        )
        self.assertFalse(state.extra["star.g161"]["geometry_available"])
        self.assertEqual(canal.get_tool_path(), [])
        self.assertEqual(canal.get_exec_nodes()[0].generated_motion_segments, [])

    def test_g161_accepts_q_zero(self):
        state = self._state()
        StarG161StepCycleHandler().handle(
            NCCommandNode(
                g_code_command={"G161"},
                command_parameter={"A": "1", "D": "1", "Q": "0"},
            ),
            state,
        )

        self.assertEqual(state.extra["star.g161"]["parameters"]["q"], 0.0)

    def test_g161_rejects_g96(self):
        state = self._state()
        state.extra["surface_speed_mode"] = SpeedMode.CONSTANT_CUTSPEED
        with self.assertRaises(ExceptionNode) as error:
            StarG161StepCycleHandler().handle(NCCommandNode(g_code_command={"G161"}, command_parameter={"Z": "-1", "A": "1", "F": "1", "D": "1", "Q": "1"}), state)
        self.assertEqual(error.exception.code, 3712)

    def test_g161_rejects_g98(self):
        state = self._state()
        state.extra["feed_mode"] = FeedMode.FEED_PER_MIN
        with self.assertRaises(ExceptionNode) as error:
            StarG161StepCycleHandler().handle(NCCommandNode(g_code_command={"G161"}, command_parameter={"Z": "-1", "A": "1", "F": "1", "D": "1", "Q": "1"}), state)
        self.assertEqual(error.exception.code, 3729)

    def test_g161_accepts_endpoint_in_m40_mode(self):
        state = self._state()
        state.extra["star.machining_mode"] = "M40"
        points, duration = StarG161StepCycleHandler().handle(
            NCCommandNode(
                g_code_command={"G161"},
                command_parameter={"Z": "-1", "A": "1", "F": "1", "D": "1"},
            ),
            state,
        )

        self.assertEqual(points[-1].z, -1.0)
        self.assertGreater(duration, 0.0)

    def test_g161_requires_option_in_machining_mode(self):
        config = MachineConfig(
            name="STAR_WITHOUT_STEP_CYCLE",
            control_type="FANUC",
            variable_pattern=r"#(\d+)",
            variable_prefix="#",
            tool_range=(0, 99),
            machine_type="TURN_MILL",
        )
        state = CNCState(machine_config=config)
        state.extra.update({
            "surface_speed_mode": SpeedMode.CONSTANT_REV,
            "feed_mode": FeedMode.FEED_PER_REV,
        })
        state.spindle_speed = 1000.0
        with self.assertRaises(ExceptionNode) as error:
            StarG161StepCycleHandler().handle(NCCommandNode(g_code_command={"G161"}, command_parameter={"Z": "-1", "A": "1", "F": "1", "D": "1", "Q": "1"}), state)
        self.assertEqual(error.exception.code, 3727)

    def test_g161_rejects_unsupported_words(self):
        state = self._state()
        with self.assertRaises(ExceptionNode) as error:
            StarG161StepCycleHandler().handle(
                NCCommandNode(g_code_command={"G161"}, command_parameter={"X": "1"}),
                state,
            )
        self.assertEqual(error.exception.code, 3730)

    def test_g161_validates_amplitude_and_rotation_ranges(self):
        state = self._state()
        for word, value in (("A", "6"), ("D", "0")):
            parameters = {"Z": "-1", "A": "1", "F": "1", "D": "1", "Q": "1"}
            parameters[word] = value
            with self.subTest(word=word, value=value), self.assertRaises(ExceptionNode) as error:
                StarG161StepCycleHandler().handle(
                    NCCommandNode(g_code_command={"G161"}, command_parameter=parameters),
                    state,
                )
            self.assertEqual(error.exception.code, 3730)


if __name__ == "__main__":
    unittest.main()