import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionNode, ExceptionTyps
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.lexers.fanuc_program_lexer import FanucProgramLexer
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenControl
from ncplot7py.infrastructure.parsers.fanuc_command_parser import FanucCommandParser


class TestFanucAlarm(unittest.TestCase):
    def test_alarm_stops_execution_and_is_returned_in_state(self):
        state = CNCState(machine_config=get_machine_config("FANUC_MILL"))
        control = UniversalConfigDrivenControl(init_nc_states=[state])
        lexer = FanucProgramLexer()
        parser = FanucCommandParser()
        program = "#100=7\n#3000=#100(TOOL NOT FOUND)\n#101=9"
        nodes = [parser.parse(statement.text, statement.line) for statement in lexer.lex(program)]

        with self.assertRaises(ExceptionNode) as caught:
            control.run_nc_code_list(nodes, 1)

        self.assertEqual(caught.exception.typ, ExceptionTyps.CNCError)
        self.assertEqual(caught.exception.code, 3007)
        self.assertEqual(caught.exception.message, "TOOL NOT FOUND")
        self.assertEqual(state.extra["alarms"], [{"code": 3007, "message": "TOOL NOT FOUND", "line": 2}])
        self.assertNotIn("101", state.parameters)

    def test_m99_stops_before_unreached_alarm(self):
        state = CNCState(machine_config=get_machine_config("FANUC_MILL"))
        control = UniversalConfigDrivenControl(init_nc_states=[state])
        lexer = FanucProgramLexer()
        parser = FanucCommandParser()
        program = "#1=1\nIF[#1=2]GOTO200\nM99\nN200\n#3000=1(TEST)"
        nodes = [parser.parse(statement.text, statement.line) for statement in lexer.lex(program)]

        control.run_nc_code_list(nodes, 1)

        self.assertNotIn("alarms", state.extra)
        self.assertNotIn(nodes[-1], control.get_exected_nodes(1))


if __name__ == "__main__":
    unittest.main()