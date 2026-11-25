"""Pin the trace-only capture experiment while preserving native acquisition guards."""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

_SOURCE = Path(__file__).resolve().parents[2] / "scripts/experts-staging/browser.py"
_BASE_SOURCE_SHA256 = "8f6c2a84d67b436ae67dc7ca0a05487d25fe076641bfcb69c8ebbd84ac4a3aca"
_BASE_FUNCTION_LINES = (
    ("loaded_fonts", 35, 44),
    ("capture", 47, 66),
    ("assert_public_body", 69, 82),
    ("capture_observation", 85, 110),
    ("write_json", 113, 120),
    ("capture_guest", 123, 144),
    ("assert_design_names", 147, 163),
    ("real_guest_clipboard", 166, 195),
    ("observe_receipts", 198, 212),
    ("prepare_real_clipboard", 215, 227),
    ("restrict_requests", 230, 242),
    ("main", 245, 265),
    ("run_readiness", 268, 297),
    ("perform_readiness", 300, 326),
)
_NORMAL_TRACE = "context.tracing.start(screenshots=True, snapshots=True, sources=True)"
_EXPERIMENT_TRACE = (
    "context.tracing.start(screenshots=False, snapshots=True, sources=True)"
)
_VIEWPORTS = (
    (1280, 800),
    (1920, 1080),
    (1512, 982),
    (768, 1024),
    (1024, 768),
    (390, 844),
    (360, 800),
)


def _method(name: str) -> ast.FunctionDef:
    """Read one actual reviewed acquisition function without importing Playwright.

    :param name: Exact known module-level function.
    :return: Its real source AST.
    :raises AssertionError: The named lifecycle function was removed or duplicated.
    """
    rows = [
        node
        for node in ast.parse(_SOURCE.read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    assert len(rows) == 1
    return rows[0]


def _call(method: str, name: str) -> ast.Call:
    """Find one actual capture call and reject omissions or duplicate calls.

    :param method: Exact containing function.
    :param name: Exact unparsed target expression.
    :return: Actual source call.
    :raises AssertionError: A named capture step was removed or duplicated.
    """
    calls = [
        node
        for node in ast.walk(_method(method))
        if isinstance(node, ast.Call) and ast.unparse(node.func) == name
    ]
    assert len(calls) == 1
    return calls[0]


def test_trace_with_preview_bitmaps_disabled_retains_dom_snapshots_and_sources() -> (
    None
):
    call = _call("run_readiness", "context.tracing.start")
    values = {keyword.arg: ast.literal_eval(keyword.value) for keyword in call.keywords}
    assert values == {"screenshots": False, "snapshots": True, "sources": True}


def test_browser_with_only_trace_preview_experiment_preserves_every_other_source_byte() -> (
    None
):
    source = _SOURCE.read_text()
    restored = source.replace(_EXPERIMENT_TRACE, _NORMAL_TRACE)
    assert hashlib.sha256(restored.encode()).hexdigest() == _BASE_SOURCE_SHA256


def test_browser_with_trace_experiment_preserves_all_diagnostic_function_line_ranges() -> (
    None
):
    rows = tuple(
        (node.name, node.lineno, node.end_lineno)
        for node in ast.parse(_SOURCE.read_text()).body
        if isinstance(node, ast.FunctionDef)
    )
    assert rows == _BASE_FUNCTION_LINES


def test_native_capture_with_trace_preview_disabled_keeps_both_full_page_png_sites() -> (
    None
):
    for method in ("capture_observation", "real_guest_clipboard"):
        call = _call(method, "page.screenshot")
        values = {keyword.arg: keyword.value for keyword in call.keywords}
        assert ast.literal_eval(values["full_page"]) is True
    source = _SOURCE.read_text()
    assert 'screenshot = f"screenshots/{name}.png"' in source
    assert '"screenshots/guest-native-clipboard.png"' in source


def test_native_video_with_trace_experiment_keeps_full_size_and_context_security() -> (
    None
):
    call = _call("run_readiness", "browser.new_context")
    values = {keyword.arg: keyword.value for keyword in call.keywords}
    assert ast.literal_eval(values["record_video_size"]) == {
        "width": 1280,
        "height": 720,
    }
    assert ast.unparse(values["record_video_dir"]) == "str(_OUTPUT / 'video')"
    assert ast.literal_eval(values["ignore_https_errors"]) is False
    assert ast.literal_eval(values["service_workers"]) == "block"


def test_guest_capture_with_trace_experiment_keeps_all_seven_ordered_viewports() -> (
    None
):
    tree = ast.parse(_SOURCE.read_text())
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "_VIEWPORTS"
            for target in node.targets
        )
    ]
    assert len(assignments) == 1
    assert ast.literal_eval(assignments[0].value) == _VIEWPORTS
