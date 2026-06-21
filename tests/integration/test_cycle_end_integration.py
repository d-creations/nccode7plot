import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ncplot7py.application.nc_execution import NCExecutionEngine
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenControl
from ncplot7py.domain.machines import get_machine_config, MachineConfig
from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.shared import configure_logging, configure_i18n

class TestCycleEndIntegration(unittest.TestCase):
    def setUp(self):
        configure_logging(console=False, web_buffer=True)
        configure_i18n()
        
    def test_cycle_end_fanuc_m20_integration(self):
        program = """
        G0 X0 Y0
        G1 X10 F200
        M20
        G0 X20  (This block runs, because it's after the FIRST M20)
        M20     (Second M20 triggers the cutoff)
        G0 X30  (Should not be reached)
        """
        
        config = get_machine_config("FANUC_GENERIC")
        config.cycle_start_code = "M20"
        state = CNCState(machine_config=config)
        ctrl = UniversalConfigDrivenControl(init_nc_states=[state])
        engine = NCExecutionEngine(ctrl)
        
        result = engine.get_Syncro_plot([program], synch=False)
        
        # In base_stateful_control, canal keys often start at 1
        executed_nodes = engine.cnc_control.get_exected_nodes(1)
        
        executed_x_20 = 0
        executed_x_30 = 0
        for node in executed_nodes:
            params = node.command_parameter
            if "X" in params:
                x_val = float(params["X"])
                if x_val == 20.0:
                    executed_x_20 += 1
                elif x_val == 30.0:
                    executed_x_30 += 1
                    
        self.assertEqual(executed_x_20, 1, "Execution should execute intermediate X20.")
        self.assertEqual(executed_x_30, 0, "Execution should stop at the second M20, preventing X30.")

    def test_cycle_end_siemens_start_label_integration(self):
        program = """
        G0 X0 Y0
        G1 X10 F200
        START:
        G0 X20  (Runs after the first label)
        START:  (Second label stops it)
        G0 X30  (Should not be reached)
        """
        
        config = get_machine_config("SIEMENS_840DI")
        if not config or config.name == "FANUC_GENERIC":
            config = MachineConfig(
                name="SIEMENS_840DI", control_type="SIEMENS",
                variable_pattern="R(\\d+)", variable_prefix="R", tool_range=(0, 9999)
            )
        config.cycle_start_code = "START:"
        state = CNCState(machine_config=config)
        ctrl = UniversalConfigDrivenControl(init_nc_states=[state])
        engine = NCExecutionEngine(ctrl)
        
        result = engine.get_Syncro_plot([program], synch=False)
        
        executed_nodes = engine.cnc_control.get_exected_nodes(1)
        
        executed_x_20 = 0
        executed_x_30 = 0
        for node in executed_nodes:
            params = node.command_parameter
            if "X" in params:
                x_val = float(params["X"])
                if x_val == 20.0:
                    executed_x_20 += 1
                elif x_val == 30.0:
                    executed_x_30 += 1
                    
        self.assertEqual(executed_x_20, 1, "Execution should execute intermediate X20.")
        self.assertEqual(executed_x_30, 0, "Execution did not stop at second START:, executing X30.")

if __name__ == '__main__':
    unittest.main()
