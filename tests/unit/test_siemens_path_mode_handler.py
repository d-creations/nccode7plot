from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.handlers.siemens_mill_cnc.path_mode_handler import SiemensPathModeHandler
from ncplot7py.shared.nc_nodes import NCCommandNode


def test_g645_updates_siemens_path_mode():
    state = CNCState()
    handler = SiemensPathModeHandler()

    handler.handle(NCCommandNode(g_code_command={"G645"}), state)

    assert state.extra["siemens"]["path_mode"] == "G645"


def test_compcad_updates_siemens_path_mode():
    state = CNCState()
    handler = SiemensPathModeHandler()

    handler.handle(NCCommandNode(variable_command="COMPCAD"), state)

    assert state.extra["siemens"]["path_mode"] == "COMPCAD"
