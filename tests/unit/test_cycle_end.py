import pytest
from ncplot7py.domain.handlers.cycle_end import CycleEnd
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.machines import MachineConfig, get_machine_config

@pytest.fixture
def fanuc_config():
    config = get_machine_config("FANUC_GENERIC")
    config.cycle_start_code = "M20"
    return config

@pytest.fixture
def siemens_config():
    config = get_machine_config("SIEMENS_840DI")
    if not config:
        config = MachineConfig(
            name="SIEMENS_840DI", control_type="SIEMENS",
            variable_pattern="R(\\d+)", variable_prefix="R", tool_range=(0, 9999)
        )
    config.cycle_start_code = "START:"
    return config

def test_cycle_end_fanuc_m20_first_pass(fanuc_config):
    handler = CycleEnd()
    state = CNCState()
    state.machine_config = fanuc_config
    
    # Simulate an M20 block
    node = NCCommandNode(command_parameter={"M": "20"})
    
    handler.handle(node, state)
    
    assert state.extra.get("cycle_start_count") == 1
    # Check that it did not sever links on the first pass
    node_next = NCCommandNode()
    node._next_ncCode = node_next
    handler.handle(node, state)
    assert node._next_ncCode is None
    assert state.extra.get("cycle_start_count") == 1 # count stays at 1

def test_cycle_end_fanuc_m20_from_variable_command(fanuc_config):
    handler = CycleEnd()
    state = CNCState()
    state.machine_config = fanuc_config
    
    # Simulate a block with M20 misparsed into variable_command
    node = NCCommandNode(variable_command="foo M20 bar")
    
    handler.handle(node, state)
    assert state.extra.get("cycle_start_count") == 1

def test_cycle_end_siemens_start_label(siemens_config):
    handler = CycleEnd()
    state = CNCState()
    state.machine_config = siemens_config
    
    # Mapped into command_parameter by fallback letters S,T,A,R,T
    # e.g., if START: became S="TART:" -> f"{k}{v}" == "START:"
    node = NCCommandNode(command_parameter={"S": "TART:"})
    
    handler.handle(node, state)
    assert state.extra.get("cycle_start_count") == 1
    
    node_next = NCCommandNode()
    node._next_ncCode = node_next
    handler.handle(node, state)
    assert node._next_ncCode is None

def test_cycle_end_siemens_start_label_fallback(siemens_config):
    handler = CycleEnd()
    state = CNCState()
    state.machine_config = siemens_config
    
    # Or mapped into variable_command
    node = NCCommandNode(variable_command="START:")
    node_next = NCCommandNode()
    node._next_ncCode = node_next
    
    handler.handle(node, state)
    assert state.extra.get("cycle_start_count") == 1
    assert node._next_ncCode is not None
    
    handler.handle(node, state)
    assert node._next_ncCode is None

def test_cycle_end_extracts_feed_and_spindle(fanuc_config):
    handler = CycleEnd()
    state = CNCState()
    state.machine_config = fanuc_config
    
    node = NCCommandNode(command_parameter={"F": "300.5", "S": "1200"})
    
    handler.handle(node, state)
    
    assert state.feed_rate == 300.5
    assert state.spindle_speed == 1200.0
