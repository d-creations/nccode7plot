from ncplot7py.infrastructure.parsers.nc_command_parser import NCCommandStringParser
parser = NCCommandStringParser()
with open('data/nc-examples/test_adv_siemens.mpf') as f:
    for i, line in enumerate(f):
        line = line.strip()
        if not line or line.startswith(';'): continue
        try:
            node = parser.parse(line, i+1)
            if node.variable_command:
                 pass
        except Exception as e:
            print(f'Line {i+1}: {e}')
