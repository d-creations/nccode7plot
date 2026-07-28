"""Control-flow handler for simple loop constructs in NC programs.

Supports a small subset of constructs found in some controllers:
- GOTO<pos>
- IF<cond> ... GOTO<pos>
- WHILE<cond> DO<pos> / END<pos> (basic skip-if-false behaviour)

This handler manipulates node linked pointers (`_next_ncCode`) so the
canal execution loop can jump to the desired node. It expects nodes to be
linked via `_next_ncCode` and `_before_ncCode` beforehand.
"""
from __future__ import annotations

import re
from typing import Optional, Tuple
import logging

from ncplot7py.domain.exec_chain import Handler
from ncplot7py.shared.nc_nodes import NCCommandNode
from ncplot7py.domain.cnc_state import CNCState
from ncplot7py.domain.expression_evaluator import ExpressionEvaluator


class ControlFlowHandler(Handler):
    TOKEN_RE = re.compile(r"(GOTO|THEN|IF|END|DO|WHILE)")

    def __init__(self, next_handler: Optional[Handler] = None):
        super().__init__(next_handler=next_handler)
        # use expression evaluator for evaluations
        self._eval_helper = ExpressionEvaluator()
        # runtime maps (populated by canal before execution)
        self._n_map = None
        self._do_map = None
        self._end_map = None
        self._nodes = None
        self._default_next = {}
        self._do_to_end = {}
        self._end_to_do = {}
        self._loop_counters = {}

    def setup_maps(self, nodes: list[NCCommandNode]) -> None:
        """Precomputes lookup maps for N-labels and DO/END loops.
        Called by the canal before execution begins.
        """
        self._nodes = nodes
        self._n_map = {}
        self._do_map = {}
        self._end_map = {}
        self._default_next = {
            node: getattr(node, "_next_ncCode", None) for node in self._nodes
        }
        self._do_to_end = {}
        self._end_to_do = {}
        self._loop_counters = {}
        open_do = {}

        for nd in self._nodes:
            try:
                nval = nd.command_parameter.get("N")
            except Exception:
                nval = None
            if nval is not None:
                try:
                    key = float(nval)
                    self._n_map[key] = nd
                except Exception:
                    pass
            # detect DO/END labels inside loop_command
            lc = getattr(nd, "loop_command", None)
            if lc:
                for m in re.findall(r"DO(\d+)", lc):
                    self._do_map.setdefault(m, []).append(nd)
                    open_do.setdefault(m, []).append(nd)
                for m in re.findall(r"END(\d+)", lc):
                    self._end_map.setdefault(m, []).append(nd)
                    starts = open_do.get(m)
                    if starts:
                        start = starts.pop()
                        self._do_to_end[start] = nd
                        self._end_to_do[nd] = start

    def _find_node_with_N(self, start: NCCommandNode, pos: str) -> Optional[NCCommandNode]:
        # Prefer lookup via precomputed map when available
        try:
            target = float(pos)
        except Exception:
            return None

        if getattr(self, "_n_map", None) is not None:
            return self._n_map.get(target)

        # fallback: search forward then backward
        node = start
        # search forwards
        while node is not None:
            try:
                nval = node.command_parameter.get("N")
            except Exception:
                nval = None
            if nval is not None:
                try:
                    if float(nval) == target:
                        return node
                except Exception:
                    pass
            node = getattr(node, "_next_ncCode", None)

        # search backwards
        node = start
        while node is not None:
            try:
                nval = node.command_parameter.get("N")
            except Exception:
                nval = None
            if nval is not None:
                try:
                    if float(nval) == target:
                        return node
                except Exception:
                    pass
            node = getattr(node, "_before_ncCode", None)

        return None

    def _find_end_for_do(self, start: NCCommandNode, pos: str) -> Optional[NCCommandNode]:
        # Normal execution uses the pair map built once by setup_maps().
        target = self._do_to_end.get(start)
        if target is not None:
            return target

        # Retain a linked-list fallback for direct use without setup_maps().
        node = start
        while node is not None:
            lc = node.loop_command
            if lc and f"END{pos}" in lc:
                return node
            node = getattr(node, "_next_ncCode", None)
        return None

    def _is_true(self, cond_text: str, state: CNCState) -> bool:
        logger = logging.getLogger(__name__)
        # strip surrounding brackets which may come from parsed tokens
        try:
            cond_text = cond_text.strip()
            if cond_text.startswith("[") and cond_text.endswith("]"):
                cond_text = cond_text[1:-1]
        except Exception:
            pass
        # detect operators GT, LT, GE, LE, EQ
        for op in ("GE", "LE", "GT", "LT", "EQ"):
            if op in cond_text:
                left, right = cond_text.split(op, 1)
                try:
                    lv = self._eval_helper.evaluate(left, state)
                    rv = self._eval_helper.evaluate(right, state)
                except Exception:
                    logger.debug("_is_true failed eval for cond=%s left=%s right=%s", cond_text, left, right, exc_info=True)
                    try:
                        logger.debug("_is_true state.parameters snapshot: %s", getattr(state, 'parameters', None))
                    except Exception:
                        pass
                    return False
                try:
                    vf_lv = float(lv) if lv not in ("", None) else 0.0
                    vf_rv = float(rv) if rv not in ("", None) else 0.0
                except ValueError:
                    vf_lv = 0.0
                    vf_rv = 0.0

                if op == "GT":
                    result = vf_lv > vf_rv
                    logger.debug("_is_true: %s GT %s -> %s", lv, rv, result)
                    return result
                if op == "LT":
                    result = vf_lv < vf_rv
                    logger.debug("_is_true: %s LT %s -> %s", lv, rv, result)
                    return result
                if op == "GE":
                    result = vf_lv >= vf_rv
                    logger.debug("_is_true: %s GE %s -> %s", lv, rv, result)
                    return result
                if op == "LE":
                    result = vf_lv <= vf_rv
                    logger.debug("_is_true: %s LE %s -> %s", lv, rv, result)
                    return result
                if op == "EQ":
                    result = vf_lv == vf_rv
                    logger.debug("_is_true: %s EQ %s -> %s", lv, rv, result)
                    return result
                if op == "NE":
                    result = vf_lv != vf_rv
                    logger.debug("_is_true: %s NE %s -> %s", lv, rv, result)
                    return result
        return False

    def handle(self, node: NCCommandNode, state: CNCState) -> Tuple[Optional[list], Optional[float]]:
        lc = node.loop_command
        if not lc:
            return super().handle(node, state)

        # A previous loop iteration may have changed this pointer. Always
        # begin from the immutable fall-through target captured at setup.
        if node in self._default_next:
            node._next_ncCode = self._default_next[node]

        # Insert spaces before tokens to help splitting (parser removed spaces)
        command = re.sub(self.TOKEN_RE, r" \1", lc)
        tokens = [t for t in command.split(" ") if t]

        # simple scan for IF...GOTO or plain GOTO
        for token in tokens:
            if token.startswith("IF"):
                cond = token[2:]
                if self._is_true(cond, state):
                    # find GOTO token in same command
                    for t2 in tokens:
                        if t2.startswith("GOTO"):
                            pos = t2.split("GOTO", 1)[1]
                            target = self._find_node_with_N(node, pos)
                            if target is None:
                                # nothing we can do; fallthrough
                                break
                            node._next_ncCode = target
                            break
                else:
                    # Condition false -> restore fallback pointer if previously modified
                    node._next_ncCode = self._default_next.get(node, getattr(node, "_next_ncCode", None))
                # whether true or false, stop processing IF
                break
            elif token.startswith("GOTO"):
                pos = token.split("GOTO", 1)[1]
                # GOTO may reference a DO-label or an N label
                target = None
                try:
                    key = float(pos)
                except Exception:
                    key = None
                if key is not None and getattr(self, "_n_map", None) is not None:
                    target = self._n_map.get(key)
                if target is None and getattr(self, "_do_map", None) is not None:
                    # do_map entries are lists; pick first
                    lst = self._do_map.get(pos)
                    if lst:
                        target = lst[0]
                if target is None:
                    target = self._find_node_with_N(node, pos)
                if target is not None:
                    node._next_ncCode = target
                break
            elif token.startswith("WHILE"):
                cond = token[5:]
                # if condition is false, skip forward to matching END
                if not self._is_true(cond, state):
                    # find DO token to get pos
                    for t2 in tokens:
                        if t2.startswith("DO"):
                            pos = t2.split("DO", 1)[1]
                            end_node = self._find_end_for_do(node, pos)
                            if end_node is not None:
                                node._next_ncCode = getattr(end_node, "_next_ncCode", None)
                            break
                # otherwise, continue into loop (no change, check next token)
                continue
            elif token.startswith("DO"):
                # DO may be a label or start of a counted loop. If the DO node
                # provides parameter 'L' we treat it as a loop counter.
                label = token[2:]
                # initialize loop counter if present on this node
                try:
                    lval = node.command_parameter.get("L")
                except Exception:
                    lval = None
                if lval is not None:
                    try:
                        cnt = int(float(self._eval_helper.evaluate(str(lval), state)))
                    except Exception:
                        try:
                            cnt = int(float(lval))
                        except Exception:
                            cnt = None
                    if cnt is not None:
                        # store counter by label so END can find it
                        self._loop_counters[label] = cnt
                break
            elif token.startswith("END"):
                label = token[3:]
                do_node = self._end_to_do.get(node)
                if do_node is None:
                    # fallback: search backward for a DO with same label
                    cur = getattr(node, "_before_ncCode", None)
                    while cur is not None:
                        lc = cur.loop_command
                        if lc and f"DO{label}" in lc:
                            do_node = cur
                            break
                        cur = getattr(cur, "_before_ncCode", None)

                if do_node is not None:
                    # if there's a loop counter for this label, decrement and jump
                    cnt = self._loop_counters.get(label)
                    if cnt is not None:
                        if cnt > 1:
                            self._loop_counters[label] = cnt - 1
                            node._next_ncCode = getattr(do_node, "_next_ncCode", do_node)
                        else:
                            # completed loop
                            del self._loop_counters[label]
                    else:
                        # If this DO was actually a WHILE (e.g. "WHILE[...]DO<label>"),
                        # re-evaluate the condition here and jump back to the DO body
                        # if the condition still holds.
                        try:
                            lc = do_node.loop_command
                        except Exception:
                            lc = None
                        if lc and "WHILE" in lc:
                            # extract WHILE token and condition similar to above
                            command2 = re.sub(self.TOKEN_RE, r" \1", lc)
                            tokens2 = [t for t in command2.split(" ") if t]
                            for t3 in tokens2:
                                if t3.startswith("WHILE"):
                                    cond_text = t3[5:]
                                    try:
                                        if self._is_true(cond_text, state):
                                            # condition still true -> jump back into loop body
                                            node._next_ncCode = getattr(do_node, "_next_ncCode", do_node)
                                        else:
                                            # condition false -> ensure END falls through to next node
                                            node._next_ncCode = self._default_next.get(
                                                node, getattr(node, "_next_ncCode", None)
                                            )
                                    except Exception:
                                        # on error, fall through
                                        pass
                                    break
                break

        return super().handle(node, state)


__all__ = ["ControlFlowHandler"]
