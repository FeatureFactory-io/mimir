"""Keep wire validation strict across supported MCP SDK model representations."""

from __future__ import annotations

import json

import pytest
from fastmcp import Client, FastMCP
from mcp.types import JSONRPCNotification, JSONRPCResponse
from pydantic import ValidationError

from tests.support import karma_mcp


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"jsonrpc": "2.0", "id": 1, "result": {"ready": True}}, JSONRPCResponse),
        (
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            JSONRPCNotification,
        ),
    ],
)
def test_protocol_decoder_with_actual_wire_message_preserves_typed_envelope(
    payload: dict[str, object], expected: type
) -> None:
    """Validate actual response and notification shapes without a protocol double."""
    message = karma_mcp._decode_jsonrpc_message(json.dumps(payload).encode())
    assert isinstance(message, expected)
    assert message.model_dump(mode="json", exclude_unset=True) == payload


@pytest.mark.parametrize(
    "payload", [b"not json", b"{}", b'{"jsonrpc":"1.0","id":1,"result":{}}']
)
def test_protocol_decoder_with_malformed_wire_message_rejects(payload: bytes) -> None:
    """A representation upgrade cannot allow malformed JSON-RPC envelopes."""
    with pytest.raises((ValidationError, AssertionError)):
        karma_mcp._decode_jsonrpc_message(payload)


@pytest.mark.asyncio
async def test_payload_decoder_with_real_empty_collection_retains_successful_empty_list() -> (
    None
):
    """Exercise real SDK serialization of a collection containing no rows."""
    server = FastMCP("empty-collection-proof")

    @server.tool
    def read_collection() -> list:
        """Return an actual empty public metadata collection."""
        return []

    async with Client(server) as client:
        result = await client.call_tool("read_collection")
    payload = karma_mcp.decode_tool_payload(result, allow_empty_collection=True)
    assert payload == [] or payload == {"result": []}
    if result.content == [] and result.structured_content is None:
        with pytest.raises(AssertionError, match="one JSON"):
            karma_mcp.decode_tool_payload(result)


@pytest.mark.parametrize(
    "result",
    [
        {"isError": True, "content": []},
        {"content": []},
        {"content": [{"type": "text", "text": "not json"}]},
        {"content": [{"type": "image", "text": "[]"}]},
        {"content": [{"type": "text", "text": "[]"}] * 2},
    ],
)
def test_payload_decoder_with_invalid_or_error_result_rejects(
    result: dict[str, object],
) -> None:
    """Empty collection support cannot manufacture a payload from an invalid result."""
    with pytest.raises((AssertionError, ValueError)):
        karma_mcp.decode_tool_payload(result)
