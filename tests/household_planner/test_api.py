"""HTTP tests with authentication dependency overridden; never exercises LDAP authentication."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from mealie.core.dependencies.dependencies import get_current_user, get_integration_id
from mealie.db.db_setup import generate_session
from mealie.db.models._model_base import SqlAlchemyBase
from mealie.routes.households.controller_household_planner import router


@pytest.fixture
def api():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    SqlAlchemyBase.metadata.create_all(engine)
    app = FastAPI()
    app.include_router(router, prefix="/api")
    person = SimpleNamespace(id=uuid4(), group_id=uuid4(), household_id=uuid4())

    def db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[generate_session] = db
    app.dependency_overrides[get_current_user] = lambda: person
    app.dependency_overrides[get_integration_id] = lambda: "planner-test"
    with TestClient(app) as client:
        yield client, person
    engine.dispose()


BASE = "/api/households/planning"


def test_personal_scope_and_delete_derived_health(api):
    client, person = api
    original = person.id
    profile = {"gluten_free": True, "birth_date": "1990-01-01"}
    assert client.put(BASE + "/me/profile?revision=0", json=profile).status_code == 200
    obs = {"id": "sample1", "kind": "weight_kg", "value": 80, "at": "2026-10-14T00:00:00Z", "source": "fixture"}
    result = client.post(BASE + "/me/health?revision=1", json={"observations": [obs]})
    assert result.status_code == 200
    assert result.json()["revision"] == 2
    person.id = uuid4()
    assert client.get(BASE + "/me").json()["state"]["observations"] == {}
    assert client.get(BASE + "/me").json()["state"]["profile"]["birth_date"] is None
    assert "observations" not in client.get(BASE).json()["state"]
    person.id = original
    assert client.post(BASE + "/me/health?revision=1", json={"observations": []}).status_code == 409
    assert client.delete(BASE + "/me/health?revision=2").json()["state"]["observations"] == {}


def test_goals_require_separate_confirmation(api):
    client, _ = api
    response = client.post(BASE + "/me/goals/manual?revision=0", json={"calories": 2100, "protein": 100})
    assert response.status_code == 200
    assert response.json()["state"]["active"] is None
    goal = response.json()["state"]["revisions"][0]["id"]
    response = client.post(BASE + f"/me/goals/{goal}/confirm?revision=1")
    assert response.status_code == 200
    assert response.json()["state"]["active"]["goals"]["calories"] == 2100
    assert response.json()["review_due"] is False


def test_invalid_health_and_foreign_allocations(api):
    client, _ = api
    assert (
        client.post(
            BASE + "/me/health?revision=0",
            json={
                "observations": [
                    {"id": "x", "kind": "weight_kg", "value": 0, "at": "2026-10-14T00:00:00Z", "source": "fixture"}
                ]
            },
        ).status_code
        == 422
    )
    plan = {
        "start": "2026-10-12",
        "entries": [
            {"user_id": str(uuid4()), "recipe_id": str(uuid4()), "day": "2026-10-12", "meal": "lunch", "servings": 1}
        ],
    }
    assert client.post(BASE + "/preview", json=plan).status_code == 422
    assert client.get(BASE).json()["revision"] == 0


def test_no_authentication_no_planner_access():
    app = FastAPI()
    app.include_router(router, prefix="/api")
    with TestClient(app) as client:
        assert client.get(BASE).status_code in (401, 403)


def test_backup_preserves_nested_planner_contract():
    from copy import deepcopy

    from mealie.services.backups_v2.alchemy_exporter import AlchemyExporter

    payload = {
        "plans": {
            "sample": {"id": str(uuid4()), "checked_items": ["rice|raw"], "confirmed_at": "2026-10-14T00:00:00Z"}
        },
        "observations": {},
    }
    dump = {
        "household_planner_documents": [
            {
                "id": "user:fixture",
                "revision": 1,
                "payload": deepcopy(payload),
                "created_at": "2026-10-14T00:00:00",
                "update_at": "2026-10-14T00:00:00",
            }
        ]
    }
    exporter = AlchemyExporter("sqlite://")
    converted = exporter.convert_types(dump)
    assert converted["household_planner_documents"][0]["payload"] == payload
    assert converted["household_planner_documents"][0]["created_at"].year == 2026
    exporter.engine.dispose()


def test_week_endpoint_validates_start_and_accepts_empty_week(api):
    client, _ = api
    assert (
        client.put(BASE + "/weeks/2026-10-19?revision=0", json={"start": "2026-10-12", "entries": []}).status_code
        == 422
    )
    response = client.put(BASE + "/weeks/2026-10-12?revision=0", json={"start": "2026-10-12", "entries": []})
    assert response.status_code == 200 and response.json()["state"]["plans"] == {}
