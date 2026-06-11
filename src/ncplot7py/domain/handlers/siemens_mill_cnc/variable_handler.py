"""Siemens 840D variable and expression handling."""
from __future__ import annotations

import ast
import math
import re
from typing import Any, Dict, Optional, Tuple

from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.handlers.siemens_mill_cnc.common import ensure_siemens_scope, format_number


def _atan2_deg(y_value: float, x_value: float) -> float:
    return math.degrees(math.atan2(y_value, x_value))


def _sin_deg(value: float) -> float:
    return math.sin(math.radians(value))


def _cos_deg(value: float) -> float:
    return math.cos(math.radians(value))


def _tan_deg(value: float) -> float:
    return math.tan(math.radians(value))


def _asin_deg(value: float) -> float:
    return math.degrees(math.asin(value))


def _acos_deg(value: float) -> float:
    return math.degrees(math.acos(value))


def _atan_deg(value: float) -> float:
    return math.degrees(math.atan(value))


_ALLOWED_FUNCS = {
    "SQRT": math.sqrt,
    "SIN": _sin_deg,
    "COS": _cos_deg,
    "TAN": _tan_deg,
    "ASIN": _asin_deg,
    "ACOS": _acos_deg,
    "ATAN": _atan_deg,
    "ATAN2": _atan2_deg,
    "ABS": abs,
    "POT": math.pow,
    "TRUNC": math.trunc,
    "LN": math.log,
    "EXP": math.exp,
    "ROUND": round,
    "FIX": math.trunc,
    "FUP": math.ceil,
    "TRUE": True,
    "FALSE": False,
    "PI": math.pi,
}


class SiemensExpressionEvaluator:
    """Small Siemens-aware evaluator for numeric and BOOL-compatible expressions."""

    _SYSTEM_VAR_RE = re.compile(r"\$[A-Za-z0-9_]+(?:\[[^\]]+\])?")
    _R_PARAM_RE = re.compile(r"\bR(\d+)\b", re.IGNORECASE)
    _NAME_INDEX_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]")

    def evaluate(self, expression: str, state: CNCState) -> float:
        expression = str(expression or "").strip()
        if expression.startswith("="):
            expression = expression[1:].strip()
        if not expression:
            return 0.0
        return float(self._eval_python(self._to_python(expression, state), state))

    def is_true(self, expression: str, state: CNCState) -> bool:
        return bool(self._eval_python(self._to_python(expression, state), state))

    def replace_in_parameter(self, value: str, state: CNCState) -> str:
        value = str(value)
        if "=" in value:
            # Safely handle both "=EXPR" and buggy "A=EXPR" from parser overlaps
            _, expr = value.split("=", 1)
            return format_number(self.evaluate(expr, state))
        try:
            return format_number(self.evaluate(value, state))
        except Exception:
            return value

    def _to_python(self, expression: str, state: CNCState) -> str:
        scope = ensure_siemens_scope(state)
        expr = expression.strip()
        if expr.startswith("[") and expr.endswith("]"):
            expr = expr[1:-1]
        expr = re.sub(r"\bAND\b", " and ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bOR\b", " or ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bNOT\b", " not ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bDIV\b", " // ", expr, flags=re.IGNORECASE)
        expr = re.sub(r"\bMOD\b", " % ", expr, flags=re.IGNORECASE)
        expr = self._replace_mnemonic_comparisons(expr)
        expr = expr.replace("<>", "!=")
        expr = self._SYSTEM_VAR_RE.sub(lambda match: str(self._read_system_variable(match.group(0), state)), expr)
        expr = self._R_PARAM_RE.sub(lambda match: f"__r_{match.group(1)}", expr)

        def replace_array(match: re.Match) -> str:
            name = match.group(1)
            if name.upper() in _ALLOWED_FUNCS:
                return match.group(0)
            index_value = int(float(self.evaluate(match.group(2), state)))
            if name in scope["arrays"]:
                values = scope["arrays"].get(name, [])
                if 0 <= index_value < len(values):
                    return str(values[index_value])
            return "0.0"

        previous = None
        while previous != expr:
            previous = expr
            expr = self._NAME_INDEX_RE.sub(replace_array, expr)
        return expr

    def _replace_mnemonic_comparisons(self, expression: str) -> str:
        replacements = {
            "GE": ">=",
            "LE": "<=",
            "GT": ">",
            "LT": "<",
            "EQ": "==",
            "NE": "!=",
        }
        expr = expression
        for mnemonic, operator in replacements.items():
            expr = re.sub(
                rf"(?<=[A-Za-z0-9_\]\)]){mnemonic}(?=[A-Za-z0-9$\[])",
                operator,
                expr,
                flags=re.IGNORECASE,
            )
            expr = re.sub(rf"\b{mnemonic}\b", operator, expr, flags=re.IGNORECASE)
        return expr

    def _read_system_variable(self, token: str, state: CNCState) -> float:
        scope = ensure_siemens_scope(state)
        match = re.match(r"^(\$[A-Za-z0-9_]+)(?:\[([^\]]+)\])?$", token)
        if not match:
            return 0.0
        name = match.group(1).upper()
        index_text = match.group(2)
        if name in {"$VA_IW", "$AA_IW", "$AA_MW"} and index_text:
            axis = index_text.strip().strip('"').upper()
            if name == "$AA_MW":
                return float(scope["system_variables"].get(f"$AA_MW[{axis}]", state.axes.get(axis, 0.0)))
            return float(state.axes.get(axis, 0.0))
        if name.startswith("$TC_DP"):
            return 0.0
        if name == "$P_UIFR" and index_text:
            return float(self.evaluate(index_text, state))
        return float(scope["system_variables"].get(token, 0.0))

    def _eval_python(self, expr: str, state: CNCState) -> Any:
        node = ast.parse(expr, mode="eval")
        allowed_nodes = (
            ast.Expression,
            ast.BinOp,
            ast.UnaryOp,
            ast.BoolOp,
            ast.Compare,
            ast.Call,
            ast.Load,
            ast.Name,
            ast.Constant,
            ast.Add,
            ast.Sub,
            ast.Mult,
            ast.Div,
            ast.Mod,
            ast.FloorDiv,
            ast.Pow,
            ast.UAdd,
            ast.USub,
            ast.And,
            ast.Or,
            ast.Not,
            ast.Eq,
            ast.NotEq,
            ast.Lt,
            ast.LtE,
            ast.Gt,
            ast.GtE,
        )
        for item in ast.walk(node):
            if not isinstance(item, allowed_nodes):
                raise ValueError(f"Unsafe Siemens expression element: {type(item).__name__}")

        class SiemensEvalContext(dict):
            def __missing__(self, key: str) -> float:
                if key.startswith("__r_"):
                    return 0.0
                return 0.0

        context = SiemensEvalContext()
        context.update(_ALLOWED_FUNCS)
        context.update(self.build_context(state))
        return eval(compile(node, "<siemens_expr>", "eval"), {"__builtins__": {}}, context)

    def build_context(self, state: CNCState) -> Dict[str, Any]:
        scope = ensure_siemens_scope(state)
        context: Dict[str, Any] = {}
        for key, value in state.parameters.items():
            context[f"__r_{key}"] = float(value)
        for key, value in scope["symbols"].items():
            try:
                context[key] = float(value)
            except Exception:
                context[key] = value
        return context


class SiemensVariableHandler(Handler):
    """Handle Siemens DEF declarations, named assignments, and parameter resolution."""

    _DEF_RE = re.compile(r"^DEF\s+(INT|REAL|BOOL|CHAR|STRING(?:\[\d+\])?|AXIS|FRAME)\s+(.+)$", re.IGNORECASE)
    _ASSIGN_RE = re.compile(r"^(.+?)\s*=\s*(.+)$")

    def __init__(self, next_handler: Optional[Handler] = None):
        super().__init__(next_handler=next_handler)
        self._evaluator = SiemensExpressionEvaluator()

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        scope = ensure_siemens_scope(state)
        command = (node.variable_command or "").strip()

        if command:
            if self._handle_definition(command, state, scope) or self._handle_assignment(command, state, scope):
                pass

        original_parameters = None
        if node.command_parameter:
            new_parameters = {key: self._evaluator.replace_in_parameter(value, state) for key, value in node.command_parameter.items()}
            original_parameters = node._command_parameter
            node._command_parameter = new_parameters

        result = super().handle(node, state)

        if original_parameters is not None:
            node._command_parameter = original_parameters
        return result

    def _handle_definition(self, command: str, state: CNCState, scope: Dict[str, Any]) -> bool:
        match = self._DEF_RE.match(command)
        if not match:
            return False
        type_name = match.group(1).upper()
        declaration = match.group(2).strip()
        name_part, init_expr = (declaration.split("=", 1) + [None])[:2] if "=" in declaration else (declaration, None)
        name_part = name_part.strip()
        array_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]$", name_part)
        if array_match:
            name = array_match.group(1)
            length = int(array_match.group(2))
            scope["types"][name] = type_name
            scope["arrays"][name] = [0.0] * length
            return True

        name = name_part.split()[0]
        scope["types"][name] = type_name
        if init_expr is not None:
            scope["symbols"][name] = self._cast_value(type_name, self._evaluator.evaluate(init_expr, state))
        else:
            scope["symbols"].setdefault(name, False if type_name == "BOOL" else 0.0)
        return True

    def _handle_assignment(self, command: str, state: CNCState, scope: Dict[str, Any]) -> bool:
        match = self._ASSIGN_RE.match(command)
        if not match:
            return False
        left = match.group(1).strip()
        right = match.group(2).strip()

        r_match = re.match(r"^R(\d+)$", left, re.IGNORECASE)
        if r_match:
            state.parameters[r_match.group(1)] = float(self._evaluator.evaluate(right, state))
            return True

        system_match = re.match(r"^(\$[A-Za-z0-9_]+(?:\[[^\]]+\])?)$", left)
        if system_match:
            if left.upper().startswith("$P_UIFR"):
                return False
            scope["system_variables"][left] = float(self._evaluator.evaluate(right, state))
            return True

        array_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*\[\s*([^\]]+)\s*\]$", left)
        if array_match:
            name = array_match.group(1)
            index = int(float(self._evaluator.evaluate(array_match.group(2), state)))
            values = scope["arrays"].setdefault(name, [])
            while len(values) <= index:
                values.append(0.0)
            values[index] = self._evaluator.evaluate(right, state)
            return True

        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", left):
            type_name = scope["types"].get(left, "REAL")
            scope["symbols"][left] = self._cast_value(type_name, self._evaluator.evaluate(right, state))
            return True
        return False

    def _cast_value(self, type_name: str, value: float) -> Any:
        if type_name == "INT":
            return int(value)
        if type_name == "BOOL":
            return bool(value)
        return float(value)


__all__ = ["SiemensExpressionEvaluator", "SiemensVariableHandler"]