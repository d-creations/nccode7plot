import pytest
import math

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.handlers.motion import MotionHandler
from ncplot7py.domain.handlers.siemens_mill_cnc.feed_handler import FeedMode
from ncplot7py.domain.handlers.siemens_mill_cnc.motion_handler import SiemensMotionHandler
from ncplot7py.domain.handlers.siemens_mill_cnc.speed_handler import SiemensSpeedMode
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenCanal
from ncplot7py.shared.nc_nodes import NCCommandNode


class CaptureMotionHandler(MotionHandler):
    def __init__(self):
        super().__init__()
        self.calls = 0

    def handle(self, node, state):
        self.calls += 1
        return super().handle(node, state)


def make_handler(next_handler=None):
    return SiemensMotionHandler(next_handler=next_handler or MotionHandler())


def test_ptp_consumes_linear_motion_as_dogleg():
    state = CNCState()
    state.feed_rate = 60.0
    handler = make_handler(CaptureMotionHandler())

    handler.handle(NCCommandNode(variable_command="PTP"), state)
    points, duration = handler.handle(NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "10", "Y": "5"}), state)

    assert duration == pytest.approx(15.0)
    assert [(point.x, point.y) for point in points] == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]
    assert state.get_axis("X") == pytest.approx(10.0)
    assert state.get_axis("Y") == pytest.approx(5.0)


def test_ptpg0_only_consumes_rapid_moves():
    state = CNCState()
    state.feed_rate = 60.0
    state.machine_config.rapid_feed_rate = 600.0
    capture = CaptureMotionHandler()
    handler = make_handler(capture)

    handler.handle(NCCommandNode(variable_command="PTPG0"), state)
    calls_after_mode = capture.calls
    rapid_points, _ = handler.handle(NCCommandNode(g_code_command={"G0"}, command_parameter={"X": "10", "Y": "5"}), state)
    assert capture.calls == calls_after_mode
    assert [(point.x, point.y) for point in rapid_points] == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0)]

    handler.handle(NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "20", "Y": "10"}), state)
    assert capture.calls == calls_after_mode + 1


def test_diam90_uses_diameter_for_g90_and_radius_for_g91():
    state = CNCState()
    state.feed_rate = 60.0
    handler = make_handler()

    handler.handle(NCCommandNode(variable_command="DIAM90"), state)
    handler.handle(NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "20"}), state)
    assert state.get_axis("X") == pytest.approx(10.0)
    assert state.get_axis_unit("X") == "diameter"

    state.set_modal("distance", "G91")
    handler.handle(NCCommandNode(g_code_command={"G1"}, command_parameter={"X": "5"}), state)
    assert state.get_axis("X") == pytest.approx(15.0)
    assert state.get_axis_unit("X") == "diameter"


def test_g95_g96_duration_uses_diamon_x_diameter():
    state = CNCState()
    state.feed_rate = 0.2
    state.spindle_speed = 200.0
    state.extra["feed_mode"] = "FEED_PER_REV"
    state.extra["surface_speed_mode"] = "CONSTANT_CUTSPEED"
    handler = make_handler()

    handler.handle(NCCommandNode(variable_command="DIAMON"), state)
    handler.handle(NCCommandNode(g_code_command={"G0"}, command_parameter={"X": "100"}), state)
    _points, duration = handler.handle(NCCommandNode(g_code_command={"G1"}, command_parameter={"Z": "-100"}), state)

    expected_rpm = 1000.0 * 200.0 / (math.pi * 100.0)
    assert duration == pytest.approx(100.0 / (0.2 * expected_rpm / 60.0))


def test_siemens_chain_applies_g95_g96_to_duration():
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        NCCommandNode(variable_command="DIAMON"),
        NCCommandNode(g_code_command={"G0"}, command_parameter={"X": "100"}),
        NCCommandNode(g_code_command={"G1", "G95", "G96"}, command_parameter={"Z": "-100", "S": "200", "F": "0.2"}),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    expected_rpm = 1000.0 * 200.0 / (math.pi * 100.0)
    assert duration == pytest.approx(100.0 / (0.2 * expected_rpm / 60.0))
    assert state.extra["surface_speed_mode"] is SiemensSpeedMode.CONSTANT_CUTSPEED


def test_siemens_g97_selects_constant_rpm_mode():
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)

    canal.run_nc_code_list([NCCommandNode(g_code_command={"G97"})])

    assert state.extra["surface_speed_mode"] is SiemensSpeedMode.CONSTANT_REV


def test_siemens_rejects_conflicting_speed_modes():
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)

    with pytest.raises(Exception):
        canal.run_nc_code_list([NCCommandNode(g_code_command={"G96", "G97"})])


def test_siemens_g93_uses_inverse_block_time():
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)

    canal.run_nc_code_list([NCCommandNode(g_code_command={"G1", "G93"}, command_parameter={"X": "100", "F": "2"})])

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(30.0)
    assert state.extra["feed_mode"] is FeedMode.INVERSE_TIME


def test_siemens_scc_overrides_machine_g96_reference_axis():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G0 X100 Y50"),
        parser.parse("G96 S200 F0.2 SCC[Y]"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    expected_rpm = 1000.0 * 200.0 / (math.pi * 100.0)
    assert duration == pytest.approx(100.0 / (0.2 * expected_rpm / 60.0))
    assert state.extra["g96_reference_axis"] == "Y"
    assert getattr(state.extra["feed_mode"], "value", state.extra["feed_mode"]) == "FEED_PER_REV"


def test_siemens_lims_caps_g96_rpm():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G0 X5"),
        parser.parse("G96 S200 F0.2 LIMS=1000"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(30.0)
    assert state.extra["spindle_speed_limit"] == pytest.approx(1000.0)


def test_siemens_g973_does_not_apply_lims():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G96 S200 LIMS=1000 F0.2"),
        parser.parse("G973 S2000"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(15.0)
    assert state.extra["spindle_speed_limit_active"] is False


def test_siemens_g26_caps_master_spindle_speed():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G0 X5"),
        parser.parse("G26 S1000"),
        parser.parse("G96 S200 F0.2"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(30.0)
    assert state.extra["spindle_speed_maximum"] == pytest.approx(1000.0)


def test_siemens_g25_applies_master_spindle_minimum():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G25 S1000"),
        parser.parse("G97 S500 F0.2"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(30.0)
    assert state.extra["spindle_speed_minimum"] == pytest.approx(1000.0)


def test_siemens_g25_g26_store_indexed_spindle_limits():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)

    canal.run_nc_code_list([
        parser.parse("G25 S1=10 S2=20"),
        parser.parse("G26 S1=1000 S2=2000"),
    ])

    assert state.extra["spindle_speed_limits"] == {
        1: {"minimum": 10.0, "maximum": 1000.0},
        2: {"minimum": 20.0, "maximum": 2000.0},
    }


def test_siemens_g26_remains_active_after_g973():
    parser = SiemensCommandParser()
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    canal = UniversalConfigDrivenCanal("C1", init_state=state)
    nodes = [
        parser.parse("G26 S1000"),
        parser.parse("G973 S2000 F0.2"),
        parser.parse("G1 Z-100"),
    ]

    canal.run_nc_code_list(nodes)

    _points, duration = canal.get_tool_path()[-1]
    assert duration == pytest.approx(30.0)


@pytest.mark.parametrize(
    ("code", "initial_feed_mode", "expected_speed_mode", "expected_feed_mode"),
    [
        ("G961", "FEED_PER_REV", "CONSTANT_CUTSPEED", "FEED_PER_MIN"),
        ("G962", "FEED_PER_REV", "CONSTANT_CUTSPEED", "FEED_PER_REV"),
        ("G971", "FEED_PER_REV", "CONSTANT_REV", "FEED_PER_MIN"),
        ("G972", "FEED_PER_REV", "CONSTANT_REV", "FEED_PER_REV"),
        ("G973", "FEED_PER_MIN", "CONSTANT_REV", "FEED_PER_REV"),
    ],
)
def test_siemens_extended_speed_modes(code, initial_feed_mode, expected_speed_mode, expected_feed_mode):
    state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
    state.extra["feed_mode"] = initial_feed_mode
    canal = UniversalConfigDrivenCanal("C1", init_state=state)

    canal.run_nc_code_list([NCCommandNode(g_code_command={code})])

    assert getattr(state.extra["surface_speed_mode"], "value", state.extra["surface_speed_mode"]) == expected_speed_mode
    assert getattr(state.extra["feed_mode"], "value", state.extra["feed_mode"]) == expected_feed_mode
