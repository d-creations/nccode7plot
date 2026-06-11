import sys, re
sys.path.append('src')
with open('src/ncplot7py/infrastructure/parsers/siemens_command_parser.py', 'r') as f:
    t = f.read()
t = t.replace('nc_line = re.sub(r"\\([^)]*\\)", "", nc_line)', '# parens')
with open('src/ncplot7py/infrastructure/parsers/siemens_command_parser.py', 'w') as f:
    f.write(t)

from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser
p = SiemensCommandParser()
print(p.parse('G1 G53 X=((APP_XP_GUD)+(RETRATEW_PLANE_INK))Y=APPROACH_POSITION_Y Z=CURRENT_Z_AXIS_VALUE A=APPROACH_POSITION_A B=APPROACH_POSITION_B C=APPROACH_POSITION_C LA1=APPROACH_POSITION_RAIL F=FEED_FAST').command_parameter)
