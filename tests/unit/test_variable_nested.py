import unittest

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.shared.nc_nodes import NCCommandNode


class TestVariableNestedExpressions(unittest.TestCase):
    def test_nested_bracket_expression_in_parameter(self):
        from ncplot7py.domain.handlers.variable import VariableHandler
        from ncplot7py.domain.exec_chain import Handler

        test_case = self
        class MockHandler(Handler):
            def handle(self, node, state):
                test_case.assertIn("Y", node.command_parameter)
                val = float(node.command_parameter["Y"])
                test_case.assertAlmostEqual(val, -3.46, places=5)
                return None, None

        state = CNCState()
        mock = MockHandler()
        vh = VariableHandler(next_handler=mock)

        # parameter with nested bracket expression
        node = NCCommandNode(g_code_command=set(), command_parameter={"Y": "[2*[-1.73]]"}, nc_code_line_nr=1)
        vh.handle(node, state)

    def test_nested_bracket_expression_in_variable_assignment(self):
        from ncplot7py.domain.handlers.variable import VariableHandler

        state = CNCState()
        vh = VariableHandler()

        node_var = NCCommandNode(g_code_command=set(), command_parameter={}, variable_command="#100=[2*[-1.73]]", nc_code_line_nr=2)
        vh.handle(node_var, state)

        self.assertIn("100", state.parameters)
        self.assertAlmostEqual(float(state.parameters["100"]), -3.46, places=6)

    def test_uppercase_trig_functions_are_evaluated(self):
        from ncplot7py.domain.handlers.variable import VariableHandler

        state = CNCState()
        state.parameters["4"] = 60.0
        vh = VariableHandler()

        node_var = NCCommandNode(g_code_command=set(), command_parameter={}, variable_command="#7=COS[#4/2]", nc_code_line_nr=3)
        vh.handle(node_var, state)

        self.assertIn("7", state.parameters)
        self.assertAlmostEqual(float(state.parameters["7"]), 0.8660254, places=6)

    def test_unbracketed_expressions_and_partial_brackets(self):
        from ncplot7py.domain.handlers.variable import VariableHandler
        from ncplot7py.domain.exec_chain import Handler

        test_case = self
        class MockHandler(Handler):
            def handle(self, node, state):
                test_case.assertIn("X", node.command_parameter)
                test_case.assertAlmostEqual(float(node.command_parameter["X"]), 50.0)
                return None, None

        state = CNCState()
        state.parameters["10"] = 100.0
        state.parameters["5"] = 4.0
        
        vh = VariableHandler()

        # Test Assignment: partial brackets
        node_var_partial = NCCommandNode(g_code_command=set(), variable_command="#6=#10/[#5-2]", command_parameter={})
        vh.handle(node_var_partial, state)
        self.assertAlmostEqual(float(state.parameters.get("6", 0.0)), 50.0)

        # Test Assignment: full brackets
        node_var_full = NCCommandNode(g_code_command=set(), variable_command="#7=[#10/[#5-2]]", command_parameter={})
        vh.handle(node_var_full, state)
        self.assertAlmostEqual(float(state.parameters.get("7", 0.0)), 50.0)

        mock = MockHandler()
        vh_axis = VariableHandler(next_handler=mock)
        
        # Test Axis parameter: partial brackets
        node_axis_partial = NCCommandNode(g_code_command=set(), command_parameter={"X": "#10/[#5-2]"})
        vh_axis.handle(node_axis_partial, state)
        
        # Test Axis parameter: full brackets
        node_axis_full = NCCommandNode(g_code_command=set(), command_parameter={"X": "[#10/[#5-2]]"})
        vh_axis.handle(node_axis_full, state)


if __name__ == "__main__":
    unittest.main()
