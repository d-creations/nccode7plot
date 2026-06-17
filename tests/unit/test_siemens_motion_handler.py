import pytest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.handlers.motion import MotionHandler
from ncplot7py.domain.handlers.siemens_mill_cnc.motion_handler import SiemensMotionHandler
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
