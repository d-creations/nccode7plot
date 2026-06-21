import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenControl
from ncplot7py.application.nc_execution import NCExecutionEngine

class TestSiemensVariableMathIntegration(unittest.TestCase):
    def test_siemens_variable_math_and_la1(self):
        program = """
DEF REAL ENDZ = 10
DEF REAL ENDZ2 = 5
DEF REAL Z_POS = 0
DEF REAL ZINKREMENT = 1.5
ENDZ = ENDZ + ENDZ2
G1 X10 Y20 LA1=ENDZ
G1 X10 Y20 LA1=(ENDZ/2 * 2)
Z_POS = Z_POS - ZINKREMENT
G1 Z=Z_POS
"""
        ctrl = UniversalConfigDrivenControl(
            count_of_canals=1, 
            init_nc_states=[CNCState(machine_config=get_machine_config('SIEMENS_840D'))] # ensure matching case from test or just SIEMENS_840D
        )
        engine = NCExecutionEngine(ctrl)
        result = engine.get_Syncro_plot([program], False)
        
        self.assertEqual(len(engine.errors), 0, f"Execution completed with errors: {engine.errors}")
        
        # Verify if variables have been correctly computed
        state = ctrl.get_nc_state(1)
        siemens = getattr(state, "extra", {}).get("siemens", {})
        symbols = siemens.get("symbols", {})
        
        self.assertEqual(symbols.get("ENDZ"), 15.0)
        self.assertEqual(symbols.get("Z_POS"), -1.5)
