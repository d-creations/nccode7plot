import unittest

from ncplot7py.infrastructure.lexers import FanucProgramLexer, SiemensProgramLexer


class TestProgramLexers(unittest.TestCase):
    def test_fanuc_splits_legacy_semicolon_statements(self):
        statements = FanucProgramLexer().lex("G1 X1;G1 X2\nM30")

        self.assertEqual(
            [(statement.text, statement.line, statement.column) for statement in statements],
            [("G1 X1", 1, 1), ("G1 X2", 1, 7), ("M30", 2, 1)],
        )

    def test_fanuc_removes_nested_comments_without_splitting_inside_them(self):
        statements = FanucProgramLexer().lex(
            "G1 X10 (outer; (inner) comment) Y20;G1 X30"
        )

        self.assertEqual([statement.text for statement in statements], ["G1 X10  Y20", "G1 X30"])

    def test_fanuc_preserves_parentheses_and_semicolons_in_strings(self):
        statements = FanucProgramLexer().lex('MSG="text (value); more";M30')

        self.assertEqual(
            [statement.text for statement in statements],
            ['MSG="text (value); more"', "M30"],
        )

    def test_siemens_semicolon_starts_comment_outside_string(self):
        statements = SiemensProgramLexer().lex(
            ';G1 X1\nMSG("value;still text") ; comment\nG1 X2 ; comment'
        )

        self.assertEqual(
            [statement.text for statement in statements],
            ["", 'MSG("value;still text") ', "G1 X2 "],
        )
        self.assertEqual([statement.line for statement in statements], [1, 2, 3])

    def test_siemens_setal_alarm_text_is_preserved(self):
        source = "SETAL(65000);failure to reach the touch point"
        statements = SiemensProgramLexer().lex(source)

        self.assertEqual(statements[0].text, source)


if __name__ == "__main__":
    unittest.main()
