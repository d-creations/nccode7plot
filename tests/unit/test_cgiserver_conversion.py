import importlib.machinery
import importlib.util
import io
import pathlib
import sys
import unittest


_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CGI_PATH = _REPO_ROOT / "scripts" / "cgiserver.cgi"


def _load_cgiserver_module():
    loader = importlib.machinery.SourceFileLoader("cgiserver_for_test", str(_CGI_PATH))
    spec = importlib.util.spec_from_loader("cgiserver_for_test", loader)
    module = importlib.util.module_from_spec(spec)
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        loader.exec_module(module)
    finally:
        sys.stdout = old_stdout
    return module


class TestCgiServerConversion(unittest.TestCase):
    def test_segment_timing_uses_plot_editor_line_number(self):
        cgiserver = _load_cgiserver_module()

        result = cgiserver.build_segments_from_engine_output(
            {
                "programExec": [1, 2, 10],
                "variables": {"1": 4.7},
                "namedVariables": {"ANGLE_Z": 36.5, "CUSTOM_MC[0]": 12.0},
                "plot": [
                    {
                        "x": [0.0, 1.0],
                        "y": [0.0, 0.0],
                        "z": [0.0, 0.0],
                        "t": 2.5,
                        "lineNumber": 10,
                    }
                ],
            }
        )

        self.assertEqual(result["segments"][0]["lineNumber"], 10)
        self.assertEqual(result["executedLines"], [10])
        self.assertEqual(result["executedNodeLines"], [1, 2, 10])
        self.assertEqual(result["variables"], {"1": 4.7})
        self.assertEqual(result["namedVariables"], {"ANGLE_Z": 36.5, "CUSTOM_MC[0]": 12.0})
        self.assertEqual(result["timing"], [2.5])
        self.assertEqual(result["lineTiming"], {"10": 2.5})

    def test_variable_only_siemens_program_does_not_fall_back_to_mock(self):
        cgiserver = _load_cgiserver_module()

        result = cgiserver.handle_execute_programs(
            [
                {
                    "program": "DEF REAL CUSTOM_MC[4]\nCUSTOM_MC[3]=12.5\nANGLE_Z=ATAN2(30,40)",
                    "machineName": "SIEMENS_840DI",
                    "canalNr": "1",
                }
            ]
        )

        canal = result["canal"]["1"]
        self.assertEqual(canal["segments"], [])
        self.assertAlmostEqual(canal["namedVariables"]["CUSTOM_MC[3]"], 12.5)
        self.assertAlmostEqual(canal["namedVariables"]["ANGLE_Z"], 36.869897, places=5)

    def test_siemens_cgi_preserves_named_variables_in_axis_expressions(self):
        cgiserver = _load_cgiserver_module()
        for axis_line in ["Y=Y_POS LA1=(R75 + Y_POS) RND = ECK_RND", "LA1=(R75 + Y_POS) Y=Y_POS RND = ECK_RND"]:
            with self.subTest(axis_line=axis_line):
                program = "\n".join(
                    [
                        "DEF REAL Y_POS = 640",
                        "DEF REAL ECK_RND = 12",
                        "R75 = -525",
                        axis_line,
                        "G1 X10",
                    ]
                )

                result = cgiserver.handle_execute_programs(
                    [
                        {
                            "program": program,
                            "machineName": "SIEMENS_840DI",
                            "canalNr": "1",
                        }
                    ]
                )

                self.assertIsNone(result.get("errors"))
                canal = result["canal"]["1"]
                self.assertAlmostEqual(canal["namedVariables"]["RND"], 12.0)
                self.assertIn(5, canal["executedNodeLines"])


if __name__ == "__main__":
    unittest.main()
