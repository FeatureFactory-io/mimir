"""Real ORM/native HTTP controls for the bounded staging summary oracle."""

from __future__ import annotations

import hashlib
import sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.core.mail import send_mail
from django.test import Client, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token

from tests.support.experts_data import CEDAR_PASSWORD, CedarDataset
from tests.support.experts_summary_data import (
    SUMMARY_SCRIPTS,
    load_summary_script,
    prepare_summary_submission,
    summary_processing_scope,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/experts-staging"))
import saga_summary_fixture as fixture
from saga_fixture import domain_rows, projections


def native_login(client: Client, actor: str) -> dict[str, Any]:
    """Record actual native login action and response without fabricating timestamps.

    :param client: Real Django HTTP client with original session handling.
    :param actor: Existing fictional Cedar username.
    :return: Exact safe actual POST302 envelope and cookie identity digest.
    """
    client.get("/auth/user/login/")
    start = fixture.now()
    response = client.post(
        "/auth/user/login/", {"username": actor, "password": CEDAR_PASSWORD}
    )
    end = fixture.now()
    assert response.status_code == 302
    return {
        "actor": actor,
        "method": "POST",
        "path": "/auth/user/login/",
        "status": 302,
        "started_at": start,
        "completed_at": end,
        "session_key_sha256": hashlib.sha256(
            client.cookies["sessionid"].value.encode()
        ).hexdigest(),
    }


def actual_logins(client: Client, baseline: dict[str, Any]) -> list[Any]:
    """Execute three source-backed sign-ins with two ordinary logout requests.

    :param client: Real original HTTP/session client.
    :param baseline: Private baseline timestamp.
    :return: Precisely validated actual login intervals.
    """
    observations = []
    for actor in ("mrodriguez", "mchen", "mrodriguez"):
        observations.append(native_login(client, actor))
        if len(observations) < 3:
            assert client.get("/auth/user/logout/").status_code == 302
    return fixture.validated_logins(
        baseline, {"login_observations": observations}, fixture.now()
    )


@pytest.mark.django_db(transaction=True)
@override_settings(SESSION_SAVE_EVERY_REQUEST=True)
@pytest.mark.parametrize(
    "fault",
    [
        None,
        "maria_token_last_login",
        "mike_token_other_login",
        "unrelated_last_login",
        "extra_session",
        "existing_token",
        "verification",
    ],
)
def test_account_delta_with_real_three_login_lifecycle_rejects_unrelated_or_misbound_effects(
    cedar_dataset: CedarDataset,
    fault: str | None,
) -> None:
    """Actual account corruption cannot acquire generic login exceptions.

    :param cedar_dataset: Real fixture in the runner-owned test database.
    :param fault: One intentional actual persisted corruption or the clean control.
    :return: None after exact clean pass or required rejection.
    """
    Token.objects.get_or_create(user=cedar_dataset.users_by_username["hkim"])
    User.objects.filter(username="hkim").update(
        last_login=timezone.now().replace(microsecond=123456)
    )
    before = domain_rows()
    baseline = {"prepared_at": fixture.now()}
    logins = actual_logins(Client(), baseline)
    fixture.account_delta(before, domain_rows(), logins)
    if fault is None:
        return
    corrupt_account(fault, cedar_dataset, logins)
    with pytest.raises(AssertionError):
        fixture.account_delta(before, domain_rows(), logins)


def corrupt_account(fault: str, cedar: CedarDataset, logins: list[Any]) -> None:
    """Introduce one real persisted fault with no mocked collaborator.

    :param fault: Explicit negative-control identity.
    :param cedar: Actual object map.
    :param logins: Exact real HTTP login windows.
    :return: None after the intended fault is persisted in the test-owned DB.
    """
    if fault in {"maria_token_last_login", "mike_token_other_login"}:
        actor = "mrodriguez" if fault.startswith("maria") else "mchen"
        Token.objects.filter(user=cedar.users_by_username[actor]).update(
            created=logins[2].started_at
        )
    elif fault == "unrelated_last_login":
        User.objects.filter(username="hkim").update(
            last_login=User.objects.get(username="hkim").last_login
            + timedelta(microseconds=1)
        )
    elif fault == "extra_session":
        Session.objects.create(
            session_key="z" * 32,
            session_data="invalid",
            expire_date=timezone.now() + timedelta(days=14),
        )
    elif fault == "existing_token":
        Token.objects.filter(user=cedar.users_by_username["hkim"]).update(
            created=timezone.now()
        )
    elif fault == "verification":
        model = User._meta.apps.get_model("accounts", "UserEmailVerification")
        model.objects.filter(user=cedar.users_by_username["hkim"]).update(
            is_verified=False
        )
    else:
        raise ValueError("Unknown negative control.")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "label",
    [
        "methodology.karmaaward",
        "methodology.activity",
        "methodology.playbookversion",
        "accounts.useronboardingstate",
    ],
)
def test_domain_delta_with_actual_submission_forbids_predecision_domain_additions(
    cedar_dataset: CedarDataset,
    label: str,
) -> None:
    """Real service submission refreshes once and accepts no unrelated insertion.

    :param cedar_dataset: Actual owned fixture.
    :param label: Model used for an explicit forbidden new-row counterexample.
    :return: None after clean precise delta and forbidden insertion rejection.
    """
    pip = prepare_summary_submission(cedar_dataset)
    change = pip.changes.get()
    baseline = {
        "pip_id": pip.pk,
        "change_id": change.pk,
        "rows": domain_rows(),
        "projections": projections(),
        "prepared_at": fixture.now(),
    }
    client = Client()
    native_login(client, "mrodriguez")
    responses = load_summary_script(
        SUMMARY_SCRIPTS / "PRF-EXPERTS-01/happy.json", change.pk
    )
    with summary_processing_scope(responses) as llm:
        assert client.post(f"/pips/{pip.pk}/submit/").status_code == 302
        assert len(llm.calls) == 2
    record = {"rows": domain_rows(), "observed_at": fixture.now()}
    fixture.domain_delta(baseline, baseline["rows"], record["rows"], False)
    fixture.validate_reviewed_values(baseline, record)
    insert_forbidden_row(label, cedar_dataset)
    with pytest.raises(AssertionError):
        fixture.domain_delta(baseline, baseline["rows"], domain_rows(), False)


def insert_forbidden_row(label: str, cedar: CedarDataset) -> None:
    """Persist one actual forbidden row in the owned test DB.

    :param label: Explicit public-history or onboarding model.
    :param cedar: Real fixture identity handles.
    :return: None after a real ORM insertion.
    """
    model = User._meta.apps.get_model(label)
    if label == "accounts.useronboardingstate":
        model.objects.create(user=cedar.users_by_username["mrodriguez"])
        return
    queryset = (
        model.objects.exclude(source_kind="release")
        if label == "methodology.karmaaward"
        else model.objects.all()
    )
    original = queryset.order_by("pk").values().first()
    assert original is not None
    values = {key: value for key, value in original.items() if key != "id"}
    if label == "methodology.karmaaward":
        values["event_identity"] = "oracle-negative:" + uuid4().hex
    elif label == "methodology.activity":
        values["name"] += " oracle negative"
    elif label == "methodology.playbookversion":
        values["version_number"] = Decimal("99.0")
    model.objects.create(**values)


def test_no_predecision_mail_with_actual_file_backend_rejects_decision_artifact(
    tmp_path: Path,
) -> None:
    """A real generated file-mail is forbidden before the staff decision.

    :param tmp_path: Runner-owned private test directory.
    :return: None after the actual file delivery is detected.
    """
    fixture.validate_no_mail(tmp_path)
    with override_settings(
        EMAIL_BACKEND="django.core.mail.backends.filebased.EmailBackend",
        EMAIL_FILE_PATH=str(tmp_path),
    ):
        assert (
            send_mail(
                "Accepted",
                "Decision: ACCEPT",
                "cedar-recording@example.com",
                ["fictional@example.com"],
            )
            == 1
        )
    with pytest.raises(AssertionError):
        fixture.validate_no_mail(tmp_path)
