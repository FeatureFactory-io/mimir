"""Real failure fixtures and complete-ledger invariants for S46."""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from decimal import Decimal
from functools import partial
from threading import Event, local

from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIHandler
from django.core.signals import request_finished, request_started
from django.db import connection, connections
from django.db.models import Model
from rest_framework.authtoken.models import Token

from methodology.models import (
    Activity,
    Agent,
    Artifact,
    KarmaAward,
    Phase,
    Playbook,
    ProcessImprovementProposal,
    Rule,
    Skill,
    Workflow,
)
from tests.support.experts_data import CedarDataset, _verify_sqlite_target

LedgerSnapshot = tuple[tuple[object, ...], ...]
DENIED_ACTOR = "esvensson"
MISSING_ENTITY_ID = 900_046
PRIVATE_BODY = "S46 protected prose absent from public errors and logs"
_PRIVATE_TITLE = "S46 Private Boundary Content"
_PRIVATE_RULE_SLUG = "s46-private-rule"
_PRIVATE_BOOK = "Cedar Bid Pricing"
_PRIVATE_PIP = "Internal staffing notes for Cedar"
_OWNER = "mrodriguez"
_BODY_FIELDS = {
    "phase": (Phase, "name", "description"),
    "agent": (Agent, "name", "description"),
    "skill": (Skill, "title", "content"),
}
_ENTITY_MODELS = {
    "activity": Activity,
    "agent": Agent,
    "artifact": Artifact,
    "phase": Phase,
    "pip": ProcessImprovementProposal,
    "playbook": Playbook,
    "rule": Rule,
    "skill": Skill,
    "workflow": Workflow,
}
ENTITY_TYPES = tuple(_ENTITY_MODELS)
SIGNAL_WAIT_SECONDS = 5


def snapshot_global_ledger() -> LedgerSnapshot:
    """Read every concrete KarmaAward field ordered by primary key.

    :return: Immutable complete rows. Example: ((1, 42, ...),).
    :raises RuntimeError: Canonical award schema is unavailable.
    """
    names = tuple(field.attname for field in KarmaAward._meta.concrete_fields)
    return tuple(KarmaAward.objects.order_by("pk").values_list(*names))


def assert_global_ledger_unchanged(before: LedgerSnapshot) -> None:
    """Compare every global award field, including attribution and time.

    :param before: Earlier complete snapshot. Example: baseline rows.
    :return: None. Example: exact equality holds.
    :raises AssertionError: Any award was inserted, deleted or modified.
    """
    assert snapshot_global_ledger() == before


def prepare_denied_target(
    dataset: CedarDataset, entity_type: str, failure: str
) -> tuple[User, int]:
    """Prepare a real private-denied or absent target with a nonstaff reader.

    :param dataset: Independently restored Cedar objects. Example: CEDAR-RFP-01.
    :param entity_type: Contract entity kind. Example: "activity".
    :param failure: Supported failure. Example: "private" or "missing".
    :return: Real actor and target PK. Example: (Elena, private_activity.pk).
    :raises ValueError: Unsupported kind or failure.
    """
    if entity_type not in _ENTITY_MODELS or failure not in ("private", "missing"):
        raise ValueError("A known entity and failure kind are required.")
    reader = dataset.users_by_username[DENIED_ACTOR]
    owner = dataset.users_by_username[_OWNER]
    assert reader.is_active and not reader.is_staff and not reader.is_superuser
    assert reader.pk != owner.pk
    if failure == "missing":
        assert (
            not _ENTITY_MODELS[entity_type]
            .objects.filter(pk=MISSING_ENTITY_ID)
            .exists()
        )
        return reader, MISSING_ENTITY_ID
    return reader, _create_private_target(dataset, owner, reader, entity_type).pk


def _create_private_target(
    dataset: CedarDataset, owner: User, reader: User, entity_type: str
) -> Model:
    """Prepare one real Cedar object and the relations its access policy follows.

    :param dataset: Real Cedar book map. Example: Maria's private book.
    :param owner: Real creator. Example: Maria.
    :param reader: Real actor outside the private boundary. Example: Elena.
    :param entity_type: Entity to persist. Example: "artifact".
    :return: ORM row. Example: an artifact from a private activity.
    :raises AssertionError: Cedar authorization or creator invariant is missing.
    """
    if entity_type == "pip":
        pip = ProcessImprovementProposal.objects.get(
            title=_PRIVATE_PIP, created_by=owner
        )
        assert pip.created_by_id != reader.pk
        pip.summary = PRIVATE_BODY
        pip.save(update_fields=["summary"])
        return pip
    book = next(
        book
        for book in dataset.playbooks_by_pk.values()
        if book.author_id == owner.pk and book.name == _PRIVATE_BOOK
    )
    # Release metadata removes the independent draft restriction from this visibility proof.
    assert book.visibility == "private" and book.can_view(owner)
    book.description, book.status, book.version = (
        PRIVATE_BODY,
        "released",
        Decimal("1.0"),
    )
    book.save(update_fields=["description", "status", "version"])
    assert not book.can_view(reader)
    if entity_type == "playbook":
        return book
    return _create_private_child(book, entity_type)


def _create_private_child(book: Playbook, entity_type: str) -> Model:
    """Store protected content under the actual private playbook hierarchy.

    :param book: Private parent. Example: Maria's pricing playbook.
    :param entity_type: Requested descendant kind. Example: "rule".
    :return: ORM row. Example: a Rule with a private body.
    :raises KeyError: An unsupported kind reaches the model mapping.
    """
    if entity_type in _BODY_FIELDS:
        model, title, content = _BODY_FIELDS[entity_type]
        return model.objects.create(
            playbook=book, **{title: _PRIVATE_TITLE, content: PRIVATE_BODY}
        )
    if entity_type == "rule":
        return Rule.objects.create(
            playbook=book,
            title=_PRIVATE_TITLE,
            content=PRIVATE_BODY,
            slug=_PRIVATE_RULE_SLUG,
        )
    workflow = Workflow.objects.create(
        playbook=book, name=_PRIVATE_TITLE, description=PRIVATE_BODY
    )
    if entity_type == "workflow":
        return workflow
    activity = Activity.objects.create(
        workflow=workflow, name=_PRIVATE_TITLE, guidance=PRIVATE_BODY
    )
    if entity_type == "activity":
        return activity
    assert entity_type == "artifact"
    return Artifact.objects.create(
        playbook=book,
        produced_by=activity,
        name=_PRIVATE_TITLE,
        description=PRIVATE_BODY,
    )


def assert_no_private_data(
    dataset: CedarDataset, text: str, *, extras: Sequence[str] = ()
) -> None:
    """Check protected fixture data without printing a leaked credential on failure.

    :param dataset: The real in-scope actors. Example: Cedar.
    :param text: Actual boundary response or logs. Example: MCP error content.
    :param extras: Other sensitive values to exclude. Example: the deleted token.
    :return: None. Example: generic unavailable message.
    :raises AssertionError: Protected data was exposed.
    """
    emails = tuple(actor.email for actor in dataset.users_by_username.values())
    tokens = tuple(Token.objects.values_list("key", flat=True))
    protected = (
        PRIVATE_BODY,
        _PRIVATE_TITLE,
        _PRIVATE_RULE_SLUG,
        _PRIVATE_BOOK,
        _PRIVATE_PIP,
        *emails,
        *tokens,
        *extras,
    )
    if any(secret and secret in text for secret in protected):
        raise AssertionError("Actual boundary output exposed protected fixture data.")


@contextmanager
def revoke_token_on_next_request_finish(
    actor_id: int, *, path: str, request_id: str
) -> Iterator[Event]:
    """Revoke real credentials when the uniquely identified bundle request finishes.

    :param actor_id: Token owner PK. Example: Maria's PK.
    :param path: Actual bundle route. Example: "/api/workflows/6202/export/".
    :param request_id: Dedicated real HTTP correlation ID. Example: a UUID string.
    :return: Event set by the real request_finished receiver after deletion.
    :raises AssertionError: The intended request did not complete its revocation.
    """
    matching = local()
    revoked = Event()
    database_name = str(connections.databases["default"]["NAME"])
    identify = partial(_identify_bundle, matching, path, request_id)
    finish = partial(_finish_bundle, matching, revoked, actor_id, database_name)
    # pytest-django may dispatch through a WSGIHandler subclass.
    request_started.connect(identify, weak=False)
    request_finished.connect(finish, weak=False)
    try:
        yield revoked
        assert revoked.is_set(), "The correlated real bundle did not revoke its token."
    finally:
        request_finished.disconnect(finish)
        request_started.disconnect(identify)


def _identify_bundle(
    matching: local,
    path: str,
    request_id: str,
    *,
    sender: object,
    environ: Mapping[str, object],
    **kwargs: object,
) -> None:
    """Track only the uniquely correlated real bundle on its own request thread.

    :param matching: Thread-local association. Example: pending sender.
    :param path: Actual workflow bundle route. Example: "/api/workflows/6202/export/".
    :param request_id: Unique incoming test correlation. Example: a UUID.
    :param sender: Actual request_started emitter. Example: a live WSGI handler.
    :param environ: Actual WSGI request environment. Example: path and method.
    :param kwargs: Receiver metadata. Example: signal reference.
    :return: None. Example: one pending sender bound to this request thread.
    """
    belongs = (
        isinstance(sender, type)
        and issubclass(sender, WSGIHandler)
        and environ.get("PATH_INFO") == path
        and environ.get("REQUEST_METHOD") == "POST"
        and environ.get("HTTP_X_REQUEST_ID") == request_id
    )
    matching.sender = sender if belongs else None


def _finish_bundle(
    matching: local,
    revoked: Event,
    actor_id: int,
    database_name: str,
    *,
    sender: object,
    **kwargs: object,
) -> None:
    """Revoke the real token only once, on the matched real request completion.

    :param matching: Request-thread pending marker. Example: a WSGI handler class.
    :param revoked: Gate signalled after successful revocation. Example: Event().
    :param actor_id: Real token owner. Example: Maria's PK.
    :param database_name: Owned runner DB selected before the request.
    :param sender: Actual request_finished emitter. Example: a WSGI handler.
    :param kwargs: Actual signal metadata. Example: request_finished.
    :return: None. Example: the matching token has been revoked.
    :raises AssertionError: A real matching signal connected to the wrong DB.
    """
    expected = getattr(matching, "sender", None)
    if expected is not None and expected is sender and not revoked.is_set():
        matching.sender = None
        revoke_finished_request_token(
            actor_id=actor_id, sender=sender, database_name=database_name, **kwargs
        )
        revoked.set()


def revoke_finished_request_token(
    *, actor_id: int, sender: object, database_name: str, **kwargs: object
) -> None:
    """Delete the actual DRF token from the active live-server test database.

    :param actor_id: Token owner PK. Example: Maria's actual PK.
    :param sender: Real Django WSGI signal sender. Example: WSGIHandler.
    :param database_name: Declared runner database. Example: an owned SQLite file.
    :param kwargs: Actual signal metadata. Example: signal object.
    :return: None. Example: the following receipt authenticates unsuccessfully.
    :raises AssertionError: Signal, database or scope does not match this run.
    """
    assert isinstance(sender, type) and issubclass(sender, WSGIHandler)
    assert kwargs.get("signal") is request_finished
    assert str(connection.settings_dict["NAME"]) == database_name
    if connection.vendor == "sqlite":
        _verify_sqlite_target(database_name)
    deleted, _ = Token.objects.filter(user_id=actor_id).delete()
    assert deleted == 1
