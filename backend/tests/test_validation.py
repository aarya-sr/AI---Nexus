"""Smoke tests for the shared _validation module — the safety net under the new Builder."""

from app.agents import _validation


def _files(**kw):
    return dict(kw)


def test_imports_ast_catches_unresolved_symbol():
    files = _files(
        **{
            "agents.py": "from tools import does_not_exist\n",
            "tools.py": "def something_else():\n    return None\n",
        }
    )
    issues = _validation.validate_imports_ast(files)
    codes = [i["code"] for i in issues]
    assert "UNRESOLVED_SYMBOL" in codes


def test_imports_ast_clean_when_symbol_present():
    files = _files(
        **{
            "agents.py": "from tools import foo\n",
            "tools.py": "def foo():\n    return None\n",
        }
    )
    issues = _validation.validate_imports_ast(files)
    assert all(i["code"] != "UNRESOLVED_SYMBOL" for i in issues)


def test_tool_param_safety_flags_pydantic_reserved():
    files = _files(
        **{
            "tools.py": (
                "from crewai.tools import tool\n"
                "@tool('x')\n"
                "def x(schema: dict) -> dict:\n"
                "    return {}\n"
            )
        }
    )
    issues = _validation.validate_tool_param_safety(files)
    assert any(i["code"] == "PARAM_SHADOWS_PYDANTIC" for i in issues)


def test_crewai_tool_schema_flags_default_param():
    files = _files(
        **{
            "tools.py": (
                "from crewai.tools import tool\n"
                "@tool('x')\n"
                "def x(data: dict = None) -> dict:\n"
                "    return {}\n"
            )
        }
    )
    issues = _validation.validate_crewai_tool_schema(files)
    assert any(i["code"] == "TOOL_HAS_DEFAULTS" for i in issues)


def test_crewai_tool_schema_flags_wrong_arity():
    files = _files(
        **{
            "tools.py": (
                "from crewai.tools import tool\n"
                "@tool('x')\n"
                "def x(a, b, c) -> dict:\n"
                "    return {}\n"
            )
        }
    )
    issues = _validation.validate_crewai_tool_schema(files)
    assert any(i["code"] == "TOOL_WRONG_ARITY" for i in issues)


def test_run_all_returns_list():
    issues = _validation.run_all({"x.py": "x = 1\n"}, spec=None, framework="crewai")
    assert isinstance(issues, list)
