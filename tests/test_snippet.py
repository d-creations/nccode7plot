import sys
sys.path.append('src')
from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser
from ncplot7py.domain.handlers.siemens_mill_cnc.variable_handler import SiemensExpressionEvaluator

p = SiemensCommandParser()
lines = ["G1 G53 MEAS=1 Z=-10 A=20"]
for line in lines:
    node = p.parse(line)
    print(line)
    print(node.command_parameter)
    print(node.variable_command, node.g_code)
