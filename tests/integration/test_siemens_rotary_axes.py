import math

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenControl
from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser


def _run_siemens_program(lines):
    parser = SiemensCommandParser()
    nodes = [parser.parse(line, line_number) for line_number, line in enumerate(lines, start=1)]
    state = CNCState(machine_config=get_machine_config("SIEMENS_840D"))
    control = UniversalConfigDrivenControl(init_nc_states=[state])

    control.run_nc_code_list(nodes, 1)

    return control.get_nc_state(1), control.get_tool_path(1)


def _last_point(path):
    assert path
    return path[-1][0][-1]


def test_siemens_a_axis_rotates_yz_plane_through_full_chain():
    state, path = _run_siemens_program([
        "G0 Y50 Z0 A0",
        "G1 A90 F60",
    ])

    point = _last_point(path)

    assert math.isclose(state.get_axis("A"), 90.0, abs_tol=1e-6)
    assert math.isclose(point.x, 0.0, abs_tol=1e-6)
    assert math.isclose(point.y, 0.0, abs_tol=1e-6)
    assert math.isclose(point.z, 50.0, abs_tol=1e-6)
    assert math.isclose(point.a, 90.0, abs_tol=1e-6)


def test_siemens_b_axis_rotates_xz_plane_through_full_chain():
    state, path = _run_siemens_program([
        "G0 X50 Z0 B0",
        "G1 B90 F60",
    ])

    point = _last_point(path)

    assert math.isclose(state.get_axis("B"), 90.0, abs_tol=1e-6)
    assert math.isclose(point.x, 0.0, abs_tol=1e-6)
    assert math.isclose(point.y, 0.0, abs_tol=1e-6)
    assert math.isclose(point.z, 50.0, abs_tol=1e-6)
    assert math.isclose(point.b, 90.0, abs_tol=1e-6)


def test_siemens_c_axis_rotates_xy_plane_through_full_chain():
    state, path = _run_siemens_program([
        "G0 X0 Y50 C0",
        "G1 C180 F60",
    ])

    point = _last_point(path)

    assert math.isclose(state.get_axis("C"), 180.0, abs_tol=1e-6)
    assert math.isclose(point.x, 0.0, abs_tol=1e-6)
    assert math.isclose(point.y, -50.0, abs_tol=1e-6)
    assert math.isclose(point.z, 0.0, abs_tol=1e-6)
    assert math.isclose(point.c, 180.0, abs_tol=1e-6)