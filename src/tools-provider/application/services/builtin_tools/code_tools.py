"""Python code execution tool.

Tool for executing Python code in a restricted sandbox:
- execute_python: Run Python code with RestrictedPython
"""

import logging
from typing import Any

from .base import BuiltinToolResult, UserContext

logger = logging.getLogger(__name__)


async def execute_python(arguments: dict[str, Any], user_context: UserContext | None = None) -> BuiltinToolResult:
    """Execute Python code in a restricted sandbox."""
    code = arguments.get("code", "")
    timeout = min(arguments.get("timeout", 30), 30)

    if not code:
        return BuiltinToolResult(success=False, error="Code is required")

    logger.info(f"Executing Python code ({len(code)} chars)")

    try:
        try:
            from RestrictedPython import compile_restricted_eval, compile_restricted_exec, limited_builtins, safe_builtins, utility_builtins
            from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
            from RestrictedPython.Guards import guarded_iter_unpack_sequence, safer_getattr
        except ImportError:
            return BuiltinToolResult(
                success=False,
                error="Python execution requires RestrictedPython. Install with: pip install RestrictedPython",
            )

        import io
        import sys
        from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

        compile_result = compile_restricted_exec(code, "<agent_code>")

        if compile_result.errors:
            return BuiltinToolResult(success=False, error=f"Compilation errors: {compile_result.errors}")

        byte_code = compile_result.code

        combined_builtins = {}
        combined_builtins.update(safe_builtins)
        combined_builtins.update(limited_builtins)
        combined_builtins.update(utility_builtins)

        additional_safe_builtins = {
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "abs": abs,
            "round": round,
            "pow": pow,
            "divmod": divmod,
            "ord": ord,
            "chr": chr,
            "hex": hex,
            "oct": oct,
            "bin": bin,
            "isinstance": isinstance,
            "issubclass": issubclass,
            "callable": callable,
            "hash": hash,
            "id": id,
            "type": type,
            "zip": zip,
            "map": map,
            "filter": filter,
            "all": all,
            "any": any,
            "enumerate": enumerate,
            "iter": iter,
            "next": next,
            "slice": slice,
            "repr": repr,
            "ascii": ascii,
            "format": format,
            "bytes": bytes,
            "bytearray": bytearray,
            "memoryview": memoryview,
            "complex": complex,
            "object": object,
            "staticmethod": staticmethod,
            "classmethod": classmethod,
            "property": property,
            "super": super,
            "Exception": Exception,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "KeyError": KeyError,
            "IndexError": IndexError,
            "AttributeError": AttributeError,
            "RuntimeError": RuntimeError,
            "StopIteration": StopIteration,
            "ZeroDivisionError": ZeroDivisionError,
        }
        combined_builtins.update(additional_safe_builtins)

        import collections
        import datetime as dt
        import itertools
        import json as json_module
        import math as math_module
        import random
        import re as re_module
        import statistics
        import string

        allowed_modules = {
            "math": math_module,
            "json": json_module,
            "re": re_module,
            "datetime": dt,
            "collections": collections,
            "itertools": itertools,
            "random": random,
            "string": string,
            "statistics": statistics,
        }

        stdout_capture = io.StringIO()
        result_value = {"value": None}
        last_expr_value = {"value": None, "has_value": False}

        import ast

        try:
            tree = ast.parse(code)
            if tree.body and isinstance(tree.body[-1], ast.Expr):
                last_expr = tree.body.pop()
                if tree.body:
                    main_result = compile_restricted_exec(ast.unparse(tree), "<agent_code>")
                    if main_result.errors:
                        return BuiltinToolResult(success=False, error=f"Compilation errors: {main_result.errors}")
                    main_code = main_result.code
                else:
                    main_code = None
                expr_code_str = ast.unparse(last_expr.value)
                last_expr_value["expr_code"] = expr_code_str
            else:
                main_code = byte_code
        except SyntaxError:
            main_code = byte_code

        def execute_code():
            old_stdout = sys.stdout
            try:
                sys.stdout = stdout_capture
                local_vars: dict[str, Any] = {}
                exec_globals = {
                    "__builtins__": combined_builtins,
                    "_getattr_": safer_getattr,
                    "_getitem_": default_guarded_getitem,
                    "_getiter_": default_guarded_getiter,
                    "_iter_unpack_sequence_": guarded_iter_unpack_sequence,
                    **allowed_modules,
                }

                if main_code is not None:
                    exec(main_code, exec_globals, local_vars)  # noqa: S102  # nosec B102

                if "expr_code" in last_expr_value:
                    try:
                        eval_globals = {**exec_globals, **local_vars}
                        expr_result = compile_restricted_eval(last_expr_value["expr_code"], "<agent_expr>")
                        if expr_result.code and not expr_result.errors:
                            val = eval(expr_result.code, eval_globals, local_vars)  # noqa: S307  # nosec B307
                            last_expr_value["value"] = val
                            last_expr_value["has_value"] = True
                    except Exception as expr_err:
                        logger.debug(f"Expression evaluation failed: {expr_err}")

                if "result" in local_vars:
                    result_value["value"] = local_vars["result"]
                elif last_expr_value["has_value"]:
                    result_value["value"] = last_expr_value["value"]
                elif not result_value["value"]:
                    for var_name in ["output", "answer", "return_value", "res"]:
                        if var_name in local_vars:
                            result_value["value"] = local_vars[var_name]
                            break
            finally:
                sys.stdout = old_stdout

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(execute_code)
            try:
                future.result(timeout=timeout)
            except FuturesTimeoutError:
                return BuiltinToolResult(success=False, error=f"Execution timed out after {timeout} seconds")

        stdout_output = stdout_capture.getvalue()

        return BuiltinToolResult(
            success=True,
            result={"stdout": stdout_output, "result": result_value["value"]},
            metadata={"code_length": len(code)},
        )

    except Exception as e:
        logger.exception(f"Python execution failed: {e}")
        return BuiltinToolResult(success=False, error=f"Execution failed: {str(e)}")
