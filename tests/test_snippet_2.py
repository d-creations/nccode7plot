import sys
sys.path.append('src')
from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser

p = SiemensCommandParser()
line = "G1 G53 X=((APP_XP_GUD)+(RETRATEW_PLANE_INK))Y=APPROACH_POSITION_Y Z=CURRENT_Z_AXIS_VALUE A=APPROACH_POSITION_A B=APPROACH_POSITION_B C=APPROACH_POSITION_C LA1=APPROACH_POSITION_RAIL F=FEED_FAST"
node = p.parse(line)
print(node.command_parameter)
