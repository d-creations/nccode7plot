import unittest

from ncplot7py.infrastructure.parsers.nc_command_parser import NCCommandStringParser
from ncplot7py.domain.exceptions import ExceptionNode


class TestNCCommandParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = NCCommandStringParser()

    def test_basic_g_and_params(self):
        node = self.parser.parse("G1 X10 Y5", line_nr=7)
        self.assertIn("G1", node.g_code)
        self.assertEqual(node.command_parameter.get("X"), "10")
        self.assertEqual(node.command_parameter.get("Y"), "5")
        self.assertEqual(node.nc_code_line_nr, 7)

    def test_duplicate_parameter_raises(self):
        # Two X parameters should trigger a duplication error
        with self.assertRaises(ExceptionNode):
            self.parser.parse("X10 X20")

    def test_variable_command_capture(self):
        node = self.parser.parse("#100", line_nr=1)
        self.assertEqual(node.variable_command, "#100")
        self.assertEqual(node.g_code, set())
        self.assertEqual(node.command_parameter, {})

    def test_dddp_parsing_after_comma(self):
        node = self.parser.parse(",R10")
        # the parser places the token following the comma into dddp_command
        self.assertIn(",R10", node.dddp_command)

    def test_loop_detection(self):
        node = self.parser.parse("GOTO100", line_nr=3)
        self.assertEqual(node.loop_command, "GOTO100")
        self.assertEqual(node.g_code, set())

    def test_uppercase_trig_in_variable_command_not_split(self):
        node = self.parser.parse("#8=#7+[#5-#6]*#20*TAN[[#4/2]]+COS[#1]", line_nr=10)
        self.assertIn("TAN", node.variable_command)
        self.assertIn("COS", node.variable_command)
        self.assertEqual(node.command_parameter, {})

    def test_fanuc_parenthesis_comment_is_ignored(self):
        node = self.parser.parse("T0101(SR20 JII MODEL HEAD 1)")
        self.assertEqual(node.command_parameter.get("T"), "0101")

    def test_inline_macro_comment_is_ignored(self):
        node = self.parser.parse("#501=0.2(SUREPAISSEUR DRESSAGE)")
        self.assertIn("#501=0.2", node.variable_command)

    def test_siemens_multi_letter_commands(self):
        node = self.parser.parse("NEWCONF\nCOMPCAD\nTRAFOOF")
        self.assertEqual(node.command_parameter, {})
        self.assertEqual(node.g_code, set())

    def test_siemens_system_variables(self):
        node = self.parser.parse("$MA_COMPRESS_POS_TOL[X]=0.05")
        self.assertIn("$MA_COMPRESS_POS_TOL[X]=0.05", node.variable_command)

    def test_siemens_system_variables_to_R_parameter(self):
        node = self.parser.parse("R10=$MA_COMPRESS_POS_TOL[X]")
        self.assertIn("R10=$MA_COMPRESS_POS_TOL[X]", node.variable_command)

    def test_inline_semicolon_comments_are_ignored(self):
        node = self.parser.parse(";FRAME/NULLPUNKT==G54")
        self.assertEqual(node.command_parameter, {})
        self.assertEqual(node.g_code, set())
        
        node2 = self.parser.parse("T1 ; Fraeser Referenz=SPITZE")
        self.assertEqual(node2.command_parameter.get("T"), "1")
        self.assertNotIn("F", node2.command_parameter)
        self.assertEqual(node2.variable_command, None)

    def test_siemens_def_real_array_is_variable_command(self):
        node = self.parser.parse("DEF REAL CUSTOM_MC[30]", line_nr=11)
        self.assertEqual(node.variable_command, "DEF REAL CUSTOM_MC[30]")
        self.assertEqual(node.command_parameter, {})
        self.assertEqual(node.g_code, set())
        self.assertEqual(node.nc_code_line_nr, 11)

    def test_siemens_named_assignment_is_variable_command(self):
        node = self.parser.parse("APPROACH_POSITION_X=CURRENT_X_AXIS_VALUE")
        self.assertEqual(node.variable_command, "APPROACH_POSITION_X=CURRENT_X_AXIS_VALUE")
        self.assertEqual(node.command_parameter, {})

    def test_siemens_label_extraction_is_whole_token(self):
        node = self.parser.parse("QUADRANT_00:")
        self.assertEqual(node.variable_command, "QUADRANT_00:")
        self.assertEqual(node.command_parameter, {})
        self.assertEqual(node.loop_command, None)

    def test_siemens_gotof_label_is_loop_command(self):
        node = self.parser.parse("GOTOF QUADRANT_00")
        self.assertEqual(node.loop_command, "GOTOFQUADRANT_00")
        self.assertEqual(node.command_parameter, {})
        self.assertEqual(node.g_code, set())

    def test_siemens_for_endfor_are_loop_commands(self):
        start = self.parser.parse("For iStepsZ01=1 to NUMB_OF_MEAS")
        end = self.parser.parse("ENDFOR")
        self.assertEqual(start.loop_command, "ForiStepsZ01=1toNUMB_OF_MEAS")
        self.assertEqual(end.loop_command, "ENDFOR")
        self.assertEqual(start.command_parameter, {})
        self.assertEqual(end.command_parameter, {})

    def test_siemens_transformation_and_builtin_commands_are_masked(self):
        for source in ["TRAORI", "TRAFOOF", "SETAL(62111)", "RET"]:
            with self.subTest(source=source):
                node = self.parser.parse(source)
                self.assertEqual(node.variable_command, source)
                self.assertEqual(node.command_parameter, {})
                self.assertEqual(node.g_code, set())

    def test_siemens_setal_preserves_trailing_alarm_text(self):
        node = self.parser.parse("SETAL(62111);failure to reach the touch point")
        self.assertEqual(node.variable_command, "SETAL(62111);failure to reach the touch point")
        self.assertEqual(node.command_parameter, {})

    def test_siemens_getexet_is_kept_as_whole_command(self):
        node = self.parser.parse("GETEXET(Custom_T_AKT,Custom_THNR)")
        self.assertEqual(node.variable_command, "GETEXET(Custom_T_AKT,Custom_THNR)")
        self.assertEqual(node.command_parameter, {})

    def test_siemens_bare_anchor_lines_are_not_split_into_axis_words(self):
        for source in ["START", "Start_der_Schlaufe", "_Pre_Position", "MESSEN", "START******Definition of the variable"]:
            with self.subTest(source=source):
                node = self.parser.parse(source)
                self.assertEqual(node.variable_command, source)
                self.assertEqual(node.command_parameter, {})
                self.assertEqual(node.g_code, set())

    def test_siemens_spos_is_named_assignment(self):
        node = self.parser.parse("SPOS=180")
        self.assertEqual(node.variable_command, "SPOS=180")
        self.assertEqual(node.command_parameter, {})

    def test_siemens_g64_g53_g54_remain_g_codes(self):
        node = self.parser.parse("G64 G54 G53 X10")
        self.assertIn("G64", node.g_code)
        self.assertIn("G54", node.g_code)
        self.assertIn("G53", node.g_code)
        self.assertEqual(node.command_parameter.get("X"), "10")

    def test_siemens_named_variables_in_axis_parameters_stay_whole(self):
        node = self.parser.parse("G1 X=IDX Y=Custom_MC[1] Z=-2")
        self.assertIn("G1", node.g_code)
        self.assertEqual(node.command_parameter.get("X"), "=IDX")
        self.assertEqual(node.command_parameter.get("Y"), "=Custom_MC[1]")
        self.assertEqual(node.command_parameter.get("Z"), "=-2")

    def test_siemens_motion_line_keeps_la1_named_parameter_whole(self):
        node = self.parser.parse(
            "G1 G53 X=APPROACH_POSITION_X Y=APPROACH_POSITION_Y A=APPROACH_POSITION_A B=APPROACH_POSITION_B C=APPROACH_POSITION_C LA1=APPROACH_POSITION_RAIL F=FEED_FAST"
        )
        self.assertIn("G1", node.g_code)
        self.assertIn("G53", node.g_code)
        self.assertEqual(node.command_parameter.get("X"), "=APPROACH_POSITION_X")
        self.assertEqual(node.command_parameter.get("Y"), "=APPROACH_POSITION_Y")
        self.assertEqual(node.command_parameter.get("A"), "=APPROACH_POSITION_A")
        self.assertEqual(node.command_parameter.get("B"), "=APPROACH_POSITION_B")
        self.assertEqual(node.command_parameter.get("C"), "=APPROACH_POSITION_C")
        self.assertEqual(node.command_parameter.get("F"), "=FEED_FAST")
        self.assertEqual(node.command_parameter.get("LA1"), "=APPROACH_POSITION_RAIL")
        self.assertNotIn("L", node.command_parameter)
        self.assertEqual(node.variable_command, None)

    def test_explicit_parser_name_selects_control_family(self):
        fanuc_parser = NCCommandStringParser(parser_name="fanuc")
        fanuc_node = fanuc_parser.parse("G1 X10 Y5")
        self.assertEqual(fanuc_node.command_parameter.get("X"), "10")
        self.assertEqual(fanuc_node.variable_command, None)

        siemens_parser = NCCommandStringParser(parser_name="siemens")
        siemens_node = siemens_parser.parse("DEF REAL CUSTOM_MC[30]")
        self.assertEqual(siemens_node.variable_command, "DEF REAL CUSTOM_MC[30]")
        self.assertEqual(siemens_node.command_parameter, {})

    def test_siemens_math_assignment_and_multi_letter_axis(self):
        siemens_parser = NCCommandStringParser(parser_name="siemens")
        
        node1 = siemens_parser.parse("DEF REAL ENDZ")
        self.assertEqual(node1.variable_command, "DEF REAL ENDZ")
        self.assertEqual(node1.command_parameter, {})
        
        node2 = siemens_parser.parse("ENDZ = ENDZ + ENDZ2")
        self.assertEqual(node2.variable_command, "ENDZ = ENDZ + ENDZ2")
        self.assertEqual(node2.command_parameter, {})
        
        node3 = siemens_parser.parse("G1 X10 LA1=ENDZ")
        self.assertIn("G1", node3.g_code)
        self.assertEqual(node3.command_parameter.get("X"), "10")
        self.assertEqual(node3.command_parameter.get("LA1"), "=ENDZ")

        node4 = siemens_parser.parse("LA1=(R75 + Y_POS) Y=Y_POS RND = ECK_RND")
        self.assertEqual(node4.command_parameter.get("LA1"), "=(R75 + Y_POS)")
        self.assertEqual(node4.command_parameter.get("Y"), "=Y_POS")
        self.assertEqual(node4.variable_command, "RND = ECK_RND")

if __name__ == "__main__":
    unittest.main()
