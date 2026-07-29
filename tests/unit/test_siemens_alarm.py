import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exceptions import ExceptionNode, ExceptionTyps
from ncplot7py.domain.machines import get_machine_config
from ncplot7py.infrastructure.lexers.siemens_program_lexer import SiemensProgramLexer
from ncplot7py.infrastructure.machines.base_stateful_control import UniversalConfigDrivenControl
from ncplot7py.infrastructure.parsers.siemens_command_parser import SiemensCommandParser


class TestSiemensAlarm(unittest.TestCase):
    def test_setal_stops_execution_and_returns_quoted_message(self):
        state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
        control = UniversalConfigDrivenControl(init_nc_states=[state])
        lexer = SiemensProgramLexer()
        parser = SiemensCommandParser()
        program = 'R1=7\nSETAL(65001,"Axis distance too small")\nR2=9'
        nodes = [parser.parse(statement.text, statement.line) for statement in lexer.lex(program)]

        with self.assertRaises(ExceptionNode) as caught:
            control.run_nc_code_list(nodes, 1)

        self.assertEqual(caught.exception.typ, ExceptionTyps.CNCError)
        self.assertEqual(caught.exception.code, 65001)
        self.assertEqual(caught.exception.message, "Axis distance too small")
        self.assertEqual(state.extra["alarms"], [{"code": 65001, "message": "Axis distance too small", "line": 2}])
        self.assertNotIn("2", state.parameters)

    def test_setal_rejects_alarm_number_outside_user_range(self):
        state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
        parser = SiemensCommandParser()
        control = UniversalConfigDrivenControl(init_nc_states=[state])

        with self.assertRaises(ExceptionNode) as caught:
            control.run_nc_code_list([parser.parse("SETAL(64999)", 4)], 1)

        self.assertEqual(caught.exception.typ, ExceptionTyps.NCCodeErrors)
        self.assertIn("65000 and 69999", caught.exception.message)
        self.assertNotIn("alarms", state.extra)

    def test_setal_rejects_malformed_alarm_text(self):
        state = CNCState(machine_config=get_machine_config("SIEMENS_840DI"))
        parser = SiemensCommandParser()
        control = UniversalConfigDrivenControl(init_nc_states=[state])

        with self.assertRaises(ExceptionNode) as caught:
            control.run_nc_code_list([parser.parse("SETAL(65000,INVALID)", 5)], 1)

        self.assertEqual(caught.exception.typ, ExceptionTyps.NCCodeErrors)
        self.assertIn("Invalid SETAL syntax", caught.exception.message)
        self.assertNotIn("alarms", state.extra)


if __name__ == "__main__":
    unittest.main()