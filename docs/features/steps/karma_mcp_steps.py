"""Living-spec steps for authenticated MCP detail consumption."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID, uuid4

from asgiref.sync import async_to_sync
from behave import given, then, when
from behave.runner import Context
from django.db import connection
from django.db.models import Sum
from fastmcp.exceptions import ToolError
from pytest_django.live_server_helper import LiveServer
from rest_framework.authtoken.models import Token

from methodology.models import KarmaAward, Playbook
from methodology.models.karma_award import EventChannel
from tests.support.karma_mcp import (
    MCPCase,
    MCPClientFactory,
    MCPDataset,
    _prepare_mcp_entities,
    decode_tool_payload,
    detail_case,
)

_ACTOR_USERNAMES = {"Maria": "mrodriguez", "Mike": "mchen", "Hana": "hkim"}
_FIXTURE_KEYS = {
    "Mike's Playbook": ("get_playbook", "mike_playbook"),
    "Mike's Workflow": ("get_workflow", "mike_workflow"),
    "Mike's Phase": ("get_phase", "mike_phase"),
    "Mike's Activity": ("get_activity", "mike_activity"),
    "Mike's Skill": ("get_skill", "mike_skill"),
    "Mike's Rule": ("get_rule", "mike_rule"),
    "Mike's Agent": ("get_agent", "mike_agent"),
    "Mike's Artifact": ("get_artifact", "mike_artifact"),
    "Maria's historical Design PIP": ("get_pip", "maria_design_pip"),
}
_DETAIL_CHANNEL = EventChannel.MCP_DETAIL
_RECEIPT_PATH = "/api/consumption-receipts/"
_POINTS_PER_AWARD = 5
_MIKE_PLAYBOOK_ID = 6201
_DESIGN_PIP_KEY = "HIST-MARIA-DESIGN-01"


@contextmanager
def _live_facade_factory(dataset: MCPDataset) -> Iterator[MCPClientFactory]:
    """Serve real HTTP using the same test-owned database as simple Behave.

    :param dataset: Scenario-local Cedar fixtures with no ambient data.
    :return: Real local HTTP server behind a registered MCP client factory.
    :raises AssertionError: The runner does not own an in-memory SQLite database.
    """
    # Share the test transaction with Django's live server for serialized requests.
    assert connection.vendor == "sqlite" and connection.is_in_memory_db()
    server = LiveServer("127.0.0.1")
    try:
        yield MCPClientFactory(dataset, server.url, [])
    finally:
        server.stop()


async def _call_detail(
    factory: MCPClientFactory, case: MCPCase, event_identity: UUID
) -> object:
    """Call the registered facade and verify actual read/receipt ordering.

    :param factory: Live facade factory over the scenario's HTTP server.
    :param case: Explicit authorized actor and detail fixture.
    :param event_identity: Correlation UUID for the actual receipt.
    :return: The tool's decoded, unmodified response payload.
    :raises AssertionError: Read/receipt order or result differs.
    """
    async with factory.open(
        actor_username=case.actor_username, entrypoint="facade"
    ) as session:
        result = await session.client.call_tool(
            case.tool_name, {**case.arguments, "event_identity": str(event_identity)}
        )
        assert session.request_paths == [("GET", case.route), ("POST", _RECEIPT_PATH)]
    return decode_tool_payload(result)


def _recipient_totals() -> dict[int, int]:
    """Read every recipient's actual total from the persisted ledger."""
    return dict(
        KarmaAward.objects.values("recipient_id")
        .annotate(total=Sum("points"))
        .values_list("recipient_id", "total")
    )


def _target_playbook(case: MCPCase, dataset: MCPDataset) -> Playbook:
    """Resolve the owning playbook and author from the persisted fixture."""
    if case.tool_name == "get_pip":
        return dataset.cedar.pips_by_key[_DESIGN_PIP_KEY].playbook
    return dataset.cedar.playbooks_by_pk[_MIKE_PLAYBOOK_ID]


def _assert_detail_pair(
    case: MCPCase, event_identity: UUID, actor_id: int, playbook: Playbook
) -> None:
    """Require the exact two awards with matching immutable source snapshots."""
    awards = list(
        KarmaAward.objects.filter(
            event_identity=f"consumption:{_DETAIL_CHANNEL}:{actor_id}:{event_identity}"
        )
    )
    assert len(awards) == 2
    assert {(row.recipient_id, row.source_kind, row.points) for row in awards} == {
        (actor_id, KarmaAward.SourceKind.LEARNING, _POINTS_PER_AWARD),
        (playbook.author_id, KarmaAward.SourceKind.CONSUMPTION, _POINTS_PER_AWARD),
    }
    assert awards[0].occurred_at == awards[1].occurred_at
    for row in awards:
        assert row.category == playbook.category
        assert row.event_channel == _DETAIL_CHANNEL
        assert row.playbook_id_snapshot == playbook.pk
        assert row.entity_type_snapshot == case.tool_name.removeprefix("get_")
        assert row.entity_id_snapshot == next(iter(case.arguments.values()))
        assert row.change_id_snapshot is None


async def _assert_private_calls_rejected(
    factory: MCPClientFactory, private_book: Playbook, private_pip: MCPCase
) -> None:
    """Use a real nonstaff account to exercise both existing detail checks.

    :param factory: Live facade factory over the scenario's HTTP server.
    :param private_book: Inaccessible private playbook.
    :param private_pip: Authenticated actor without PIP creator/staff permission.
    :raises AssertionError: A denied read exposes content, posts a receipt or succeeds.
    """
    async with factory.open(
        actor_username=private_pip.actor_username, entrypoint="facade"
    ) as session:
        denied_calls = (
            (
                "get_playbook",
                {"playbook_id": private_book.pk},
                private_book.name,
                f"Playbook {private_book.pk} not found",
            ),
            (
                private_pip.tool_name,
                private_pip.arguments,
                private_pip.expected["title"],
                "Not allowed to view this PIP",
            ),
        )
        for tool_name, arguments, concealed_title, denial in denied_calls:
            try:
                await session.client.call_tool(
                    tool_name, {**arguments, "event_identity": str(uuid4())}
                )
            except ToolError as error:
                assert denial in str(error) and concealed_title not in str(error)
            else:
                raise AssertionError(f"Existing access check allowed {tool_name}.")
        assert session.request_paths == [
            ("GET", f"/api/playbooks/{private_book.pk}/"),
            ("GET", private_pip.route),
        ]


@given(
    "{consumer} has a valid MCP token and existing permission to read the independent {entity} fixture"
)
def eligible_mcp_reader(context: Context, consumer: str, entity: str) -> None:
    """Prepare the exact independently restored authorized Cedar fixture.

    :param context: AT context. Example: cedar_dataset already loaded.
    :param consumer: Fictional actor name. Example: "Mike".
    :param entity: Named imported fixture. Example: Maria's historical Design PIP.
    :return: None. Example: real token and target reference available.
    :raises AssertionError: Existing access or baseline differs.
    """
    dataset = _prepare_mcp_entities(context.cedar_dataset)
    tool, fixture_key = _FIXTURE_KEYS[entity]
    actor_username = _ACTOR_USERNAMES[consumer]
    actor = dataset.cedar.users_by_username[actor_username]
    assert actor.is_staff == (consumer == "Mike")
    case = detail_case(
        tool, dataset, actor_username=actor_username, fixture_key=fixture_key
    )
    before_count = KarmaAward.objects.count()
    token, _ = Token.objects.get_or_create(user=actor)
    response = context.client.get(case.route, HTTP_AUTHORIZATION=f"Token {token.key}")
    assert response.status_code == 200
    assert KarmaAward.objects.count() == before_count
    context.detail_dataset = dataset
    context.detail_case = case
    context.detail_event_identity = uuid4()
    context.detail_rest_content = response.json()
    context.detail_before_count = before_count
    context.detail_before_totals = _recipient_totals()


@when("the consumer reads that content using {tool}")
def read_mcp_content(context: Context, tool: str) -> None:
    """Execute the actual authorized detail and explicit receipt boundary.

    :param context: Authorized Cedar fixture and its actual REST detail response.
    :param tool: Existing detail tool name. Example: "get_pip".
    :return: None. Example: actual response stored on context.
    :raises AssertionError: Read or receipt fails.
    """
    case = context.detail_case
    assert tool == case.tool_name
    with _live_facade_factory(context.detail_dataset) as factory:
        context.detail_mcp_content = async_to_sync(_call_detail)(
            factory, case, context.detail_event_identity
        )


@then("the actual authorized entity content is returned")
def authorized_content_returned(context: Context) -> None:
    """Compare returned content with the actual selected ORM fixture.

    :param context: AT context with response. Example: historical PIP changes.
    :return: None. Example: exact authorized content asserted.
    :raises AssertionError: Wrong or fabricated payload.
    """
    case = context.detail_case
    payload = context.detail_mcp_content
    assert isinstance(payload, dict)
    assert payload == context.detail_rest_content
    assert payload["id"] == next(iter(case.arguments.values()))
    assert all(payload[field] == value for field, value in case.expected.items())
    if case.tool_name == "get_pip":
        pip = context.detail_dataset.cedar.pips_by_key[_DESIGN_PIP_KEY]
        assert payload["submitted_by_username"] == pip.created_by.username
        assert [row["name"] for row in payload["changes"]] == list(
            pip.changes.values_list("name", flat=True)
        )


@then(
    "the consumer total becomes {consumer_total:d} and target playbook author {author} becomes {author_total:d}"
)
def paired_totals(
    context: Context, consumer_total: int, author: str, author_total: int
) -> None:
    """Check recipient totals and unchanged unrelated Cedar actors.

    :param context: AT context. Example: Mike reading Hana-targeted PIP.
    :param consumer_total: Expected learner total. Example: 12455.
    :param author: Target playbook author. Example: "Hana".
    :param author_total: Expected author total. Example: 5805.
    :return: None. Example: Maria additionally remains at 8200.
    :raises AssertionError: Wrong recipient, category, amount or pair count.
    """
    case = context.detail_case
    dataset = context.detail_dataset
    people = dataset.cedar.users_by_username
    actor_id = people[case.actor_username].pk
    author_id = people[_ACTOR_USERNAMES[author]].pk
    playbook = _target_playbook(case, dataset)
    assert playbook.author_id == author_id
    before = context.detail_before_totals
    assert consumer_total - before[actor_id] == _POINTS_PER_AWARD
    assert author_total - before[author_id] == _POINTS_PER_AWARD
    assert _recipient_totals() == {
        **before,
        actor_id: consumer_total,
        author_id: author_total,
    }
    assert KarmaAward.objects.count() == context.detail_before_count + 2
    _assert_detail_pair(case, context.detail_event_identity, actor_id, playbook)


@then("private content remains protected by its existing access checks")
def private_access_preserved(context: Context) -> None:
    """Exercise existing denied private/PIP paths with real requests.

    :param context: Independently prepared AT context. Example: Maria token.
    :return: None. Example: private denial and unchanged ledger asserted.
    :raises AssertionError: Permission widened or denied read awards.
    """
    dataset = context.detail_dataset
    people = dataset.cedar.users_by_username
    assert not people[_ACTOR_USERNAMES["Hana"]].is_staff
    private_book = Playbook.objects.get(
        author=people[_ACTOR_USERNAMES["Maria"]], name="Cedar Bid Pricing"
    )
    assert private_book.visibility == "private"
    pip_case = detail_case(
        "get_pip",
        dataset,
        actor_username=_ACTOR_USERNAMES["Hana"],
        fixture_key="maria_design_pip",
    )
    before = list(KarmaAward.objects.order_by("pk").values())
    with _live_facade_factory(dataset) as factory:
        async_to_sync(_assert_private_calls_rejected)(factory, private_book, pip_case)
    assert list(KarmaAward.objects.order_by("pk").values()) == before


@given("Maria has a valid MCP token")
def maria_mcp_token(context: Context) -> None:
    """Prepare real Maria token and global before snapshot.
    :param context: Cedar AT context; example: existing context.cedar_dataset.
    :return: None; example: real authenticated Django client ready.
    :raises AssertionError: Maria baseline or token authentication differs.
    """
    raise NotImplementedError()


@when("she calls list_activities")
def list_activities_without_consumption(context: Context) -> None:
    """Call actual authorized activity collection through Django-client AT.
    :param context: Prepared token context; example: workflow 6202.
    :return: None; example: actual collection response retained.
    :raises AssertionError: Response or actual metadata is incorrect.
    """
    raise NotImplementedError()


@then("Maria remains at 8200 and Mike remains at 12450")
def maria_and_mike_unchanged(context: Context) -> None:
    """Assert exact totals plus global ledger and summary invariants.
    :param context: AT response/snapshot; example: Maria 8200, Mike 12450.
    :return: None; example: no learner, author or unrelated recipient changes.
    :raises AssertionError: Any required invariant differs.
    """
    raise NotImplementedError()
