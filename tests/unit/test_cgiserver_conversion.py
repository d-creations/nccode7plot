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
        self.assertEqual(result["timing"], [2.5])
        self.assertEqual(result["lineTiming"], {"10": 2.5})


if __name__ == "__main__":
    unittest.main()
