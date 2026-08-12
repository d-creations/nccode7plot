from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field
from copy import deepcopy
import json
import os
from importlib.resources import files

@dataclass
class MachineConfig:
    """Configuration for a specific machine/control type."""
    name: str
    control_type: str  # "FANUC", "SIEMENS"
    variable_pattern: str  # Regex for variables, e.g. r"#(\d+)" or r"R(\d+)"
    variable_prefix: str   # Prefix for variables, e.g. "#" or "R"
    tool_range: Tuple[int, int]
    parser_name: str = "fanuc"
    lexer_name: str = "fanuc"
    machine_type: str = "MILL"
    channels: int = 1
    synchronization_strategy: str = "NONE"
    supported_gcode_groups: Tuple[str, ...] = field(default_factory=tuple)
    cycle_start_code: str = ""
    default_plane: str = "G17"
    default_feed_mode: str = "FEED_PER_MIN"
    rapid_feed_rate: Optional[float] = None
    a_axis_rollover: bool = False
    b_axis_rollover: bool = False
    c_axis_rollover: bool = False
    a_axis_shortest_path: bool = False
    b_axis_shortest_path: bool = False
    c_axis_shortest_path: bool = False
    polar_interpolate_axis: str = "Y"
    diameter_axes: Tuple[str, ...] = ()
    g96_reference_axis: Optional[str] = None
    circular_threading_enabled: bool = False
    step_cycle_pro_enabled: bool = False
    rotary_axis_planes: Dict[str, str] = field(default_factory=lambda: {"A": "YZ", "B": "XZ", "C": "XY"})
    seventh_axis_name: Optional[str] = None
    seventh_axis_maps_to: Optional[str] = None
    max_execution_nodes: int = 100000
    file_extensions: Dict[str, Any] = field(default_factory=dict)
    regex_patterns: Dict[str, Any] = field(default_factory=dict)


# --- Machine Definitions ---

# Registry of configs
MACHINE_CONFIGS: Dict[str, MachineConfig] = {}

def load_machine_configs():
    global MACHINE_CONFIGS
    MACHINE_CONFIGS = {}
    try:
        try:
            config_text = files('ncplot7py').joinpath('config', 'machines.json').read_text(encoding='utf-8')
            data = json.loads(config_text)
        except (FileNotFoundError, ModuleNotFoundError, OSError):
            package_config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'machines.json')
            legacy_config_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'config', 'machines.json')
            config_path = package_config_path if os.path.exists(package_config_path) else legacy_config_path
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # First pass: load base configs
        for key, val in data.items():
            if isinstance(val, dict):
                MACHINE_CONFIGS[key] = MachineConfig(
                    name=val['name'],
                    control_type=val['control_type'],
                    variable_pattern=val['variable_pattern'],
                    variable_prefix=val['variable_prefix'],
                    parser_name=val.get('parser_name', 'siemens' if val.get('control_type') == 'SIEMENS' else 'fanuc'),
                    lexer_name=val.get('lexer_name', val.get('parser_name', 'siemens' if val.get('control_type') == 'SIEMENS' else 'fanuc')),
                    tool_range=tuple(val['tool_range']),
                    machine_type=val.get('machine_type', 'MILL'),
                    channels=val.get('channels', 1),
                    synchronization_strategy=val.get('synchronization_strategy', 'NONE'),
                    supported_gcode_groups=tuple(val.get('supported_gcode_groups', [])),
                    cycle_start_code=val.get('cycle_start_code', ''),
                    default_plane=val.get('default_plane', 'G17'),
                    default_feed_mode=val.get('default_feed_mode', 'FEED_PER_MIN'),
                    rapid_feed_rate=val.get('rapid_feed_rate'),
                    a_axis_rollover=val.get('a_axis_rollover', False),
                    b_axis_rollover=val.get('b_axis_rollover', False),
                    c_axis_rollover=val.get('c_axis_rollover', False),
                    a_axis_shortest_path=val.get('a_axis_shortest_path', False),
                    b_axis_shortest_path=val.get('b_axis_shortest_path', False),
                    c_axis_shortest_path=val.get('c_axis_shortest_path', False),
                    polar_interpolate_axis=val.get('polar_interpolate_axis', 'Y'),
                    diameter_axes=tuple(val.get('diameter_axes', [])),
                    g96_reference_axis=val.get('g96_reference_axis'),
                    circular_threading_enabled=val.get('circular_threading_enabled', False),
                    step_cycle_pro_enabled=val.get('step_cycle_pro_enabled', False),
                    rotary_axis_planes=dict(val.get('rotary_axis_planes', {"A": "YZ", "B": "XZ", "C": "XY"})),
                    seventh_axis_name=val.get('seventh_axis_name'),
                    seventh_axis_maps_to=val.get('seventh_axis_maps_to'),
                    max_execution_nodes=val.get('max_execution_nodes', 100000),
                    file_extensions=val.get('file_extensions', {}),
                    regex_patterns=val.get('regex_patterns', {})
                )
                
        # Second pass: resolve aliases
        for key, val in data.items():
            if isinstance(val, str) and val in MACHINE_CONFIGS:
                MACHINE_CONFIGS[key] = MACHINE_CONFIGS[val]
                
    except Exception as e:
        print(f"Warning: Failed to load machines.json: {e}")

load_machine_configs()

def get_machine_config(machine_name: str) -> MachineConfig:
    """Retrieve configuration for a given machine name."""
    return MACHINE_CONFIGS.get(machine_name) or MACHINE_CONFIGS.get('FANUC_MILL')

def get_machine_regex_patterns(control_type: str) -> Dict[str, Any]:
    """Return frontend regex metadata configured for a machine."""
    config = MACHINE_CONFIGS.get(control_type) or MACHINE_CONFIGS.get('FANUC_MILL')

    if config is None:
        return {}

    if config.name == 'FANUC_MILL' and control_type != 'FANUC_MILL':
        for key, c in MACHINE_CONFIGS.items():
            if c.control_type == control_type:
                config = c
                break

    return deepcopy(config.regex_patterns)

def get_available_machines() -> List[Dict[str, str]]:
    """Return a list of available machines and their control types."""
    return [
        {"machineName": key, "controlType": val.name}
        for key, val in MACHINE_CONFIGS.items()
    ]