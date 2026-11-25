"""Prove owned page cleanup while preserving native acquisition and safety checks."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any

_SOURCE = Path(__file__).resolve().parents[2] / "scripts/experts-staging/browser.py"
_BASE_UNCHANGED_FUNCTION_AST = {
    "loaded_fonts": "bca21b9ea088bfc998f89816411002f16416134095cd0aeec03cfee559b3494d",
    "capture": "bc0023505d0aa0a72594a11df435f1581138675a9627854fbf0bb6a31f6540c2",
    "assert_public_body": "77850d1fe95068b3e37b20f764e32396f7953535625b8ec1f0070e97817a5d95",
    "capture_observation": "944f723197ff1f99e248c30e8c19b4a74bf0cd2a35bdee7b126bdf7378f4143b",
    "write_json": "34046b21863f6155ea268fbff2ed5f3a52dc3616ced89e64ab2ff36932d9be80",
    "assert_design_names": "92f1f0934049f9f1c9c2931f200aae4ac09c0f75d056c81335f6f72a76127619",
    "observe_receipts": "2f6bb6db8ef55bf3a6bef045c9dbce90e4cc198f6276ca196a2f6794ef68755f",
    "prepare_real_clipboard": "ae350e4ce5a85799baa4f5b6796f20d294626c51b8ea5e6fa9f94d2cbd75b0db",
    "restrict_requests": "51df1af2d2f9e48b2ffcab5e455e2e2eb6bcd2e824073e6abe843f6e309b7e56",
    "main": "83ff6cceef633754bf3b3785720d312eef05dd0d98d7d2d8fc2c25de69288440",
    "run_readiness": "b1ccd196ddb1677d52bde9415e0838b6326fa609f5d32b93051f92298440c835",
    "perform_readiness": "6ab61563e915224931b9f5a6e919abc81231817bd39a529531b9ebc96cad7b94",
}
_GUEST_LOOP_AST = "1949bdae619a11abc812f406599415a37210e73d7f787da3e48e7340908bbb77"
_CLIPBOARD_ACTIONS_AST = (
    "46bbd5f7c843f6dec29b1e18bef1a19dda6722d61feea59865ccbb9aeeff6e3b"
)
_CLIPBOARD_ORACLE_PERMISSION_AST = (
    "db7f84da5637cd1d2c45912c1f6d521dfe16d525723fd8606d516e3308889093"
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


def _body_digest(nodes: list[ast.stmt]) -> str:
    """Compare actual acquisition semantics without relying on line indentation.

    :param nodes: Actual reviewed action statements in order.
    :return: Stable complete action-AST SHA256.
    """
    tree = ast.Module(body=nodes, type_ignores=[])
    return _semantic_digest(tree)


def _page_scope(method: str) -> ast.With:
    """Require the actual acquisition sequence to use the exclusive page owner.

    :param method: Existing guest or clipboard acquisition function.
    :return: Actual managed page block.
    :raises AssertionError: Missing, duplicated or incorrectly bound owner.
    """
    rows = [node for node in _method(method).body if isinstance(node, ast.With)]
    assert len(rows) == 1 and len(rows[0].items) == 1
    item = rows[0].items[0]
    assert ast.unparse(item.context_expr) == "owned_page(context)"
    assert ast.unparse(item.optional_vars) == "page"
    return rows[0]


def test_owned_page_with_success_or_exception_closes_actual_page_in_finally() -> None:
    owner = _method("owned_page")
    assert [ast.unparse(node) for node in owner.decorator_list] == ["contextmanager"]
    allocation = _call("owned_page", "context.new_page")
    assert allocation.args == [] and allocation.keywords == []
    guards = [node for node in owner.body if isinstance(node, ast.Try)]
    assert len(guards) == 1 and len(guards[0].body) == 1
    assert isinstance(guards[0].body[0], ast.Expr) and isinstance(
        guards[0].body[0].value, ast.Yield
    )
    assert ast.unparse(guards[0].body[0].value.value) == "page"
    assert [ast.unparse(node) for node in guards[0].finalbody] == ["page.close()"]
    assert guards[0].handlers == [] and guards[0].orelse == []


def test_guest_page_scope_with_all_fourteen_acquisitions_keeps_checks_and_order() -> (
    None
):
    scope = _page_scope("capture_guest")
    assert len(scope.body) == 1 and isinstance(scope.body[0], ast.For)
    assert _body_digest(scope.body) == _GUEST_LOOP_AST
    method = _method("capture_guest")
    assert ast.unparse(method.body[1]) == "rows = []"
    assert ast.unparse(method.body[-1]) == "return rows"


def test_clipboard_page_scope_with_native_proof_keeps_every_action_and_oracle() -> None:
    scope = _page_scope("real_guest_clipboard")
    assert _body_digest(scope.body) == _CLIPBOARD_ACTIONS_AST
    assert (
        _body_digest(_method("real_guest_clipboard").body[1:3])
        == _CLIPBOARD_ORACLE_PERMISSION_AST
    )
    assert ast.unparse(_method("real_guest_clipboard").body[3]) == "receipts = []"


def test_browser_with_page_lifecycle_fix_preserves_every_other_function_ast() -> None:
    for name, expected in _BASE_UNCHANGED_FUNCTION_AST.items():
        assert _semantic_digest(_method(name)) == expected
    created = [
        node
        for node in ast.walk(ast.parse(_SOURCE.read_text()))
        if isinstance(node, ast.Call) and ast.unparse(node.func) == "context.new_page"
    ]
    assert len(created) == 1


def test_perform_readiness_with_owned_pages_finishes_guest_before_clipboard() -> None:
    method = _method("perform_readiness")
    assignments = [node for node in method.body if isinstance(node, ast.Assign)]
    assert ast.unparse(assignments[0].value) == "capture_guest(context)"
    assert ast.unparse(assignments[1].value) == "real_guest_clipboard(context)"


def _semantic_digest(node: ast.AST) -> str:
    """Hash AST fields consistently across host3.9 and application3.14.

    :param node: Actual source AST without line/indentation metadata.
    :return: Stable complete semantic-field digest.
    """
    text = json.dumps(_semantic_value(node), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def _semantic_value(value: Any) -> Any:
    """Keep every semantic AST field, ignoring only absent empty generic metadata.

    :param value: An AST node, field list or primitive.
    :return: Stable field representation; nonempty generic changes remain visible.
    """
    if isinstance(value, ast.AST):
        fields = [
            [name, _semantic_value(item)]
            for name, item in ast.iter_fields(value)
            if name != "type_params" or item
        ]
        return [type(value).__name__, fields]
    if isinstance(value, list):
        return [_semantic_value(item) for item in value]
    return value
