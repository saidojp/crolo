"""API tests: import, editing, ownership and both quiz modes."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

# Point the app at a throwaway database *before* importing it.
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.name}"
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest")

from fastapi.testclient import TestClient  # noqa: E402

import main  # noqa: E402
from tests.conftest import JLPT_APKG, RUSSIAN_APKG  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(main.app) as test_client:
        yield test_client


def _register(client: TestClient, username: str) -> dict[str, str]:
    response = client.post(
        "/register/",
        json={
            "username": username,
            "email": f"{username}@example.com",
            "full_name": username.title(),
            "password": "secret123",
        },
    )
    assert response.status_code == 200, response.text
    token = client.post(
        "/token", data={"username": username, "password": "secret123"}
    )
    assert token.status_code == 200, token.text
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


@pytest.fixture(scope="session")
def alice(client):
    return _register(client, "alice")


@pytest.fixture(scope="session")
def bob(client):
    return _register(client, "bob")


def _upload(client: TestClient, headers, path: Path, filename: str | None = None):
    with path.open("rb") as handle:
        return client.post(
            "/decks/import",
            headers=headers,
            files={"file": (filename or path.name, handle, "application/octet-stream")},
        )


@pytest.fixture(scope="session")
def small_deck(client, alice):
    response = _upload(client, alice, RUSSIAN_APKG)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def fresh_deck(client, alice):
    """A private copy for tests that mutate a deck."""

    def _make():
        response = _upload(client, alice, RUSSIAN_APKG)
        assert response.status_code == 201, response.text
        return response.json()

    return _make


@pytest.fixture(scope="session")
def jlpt_deck(client, alice):
    response = _upload(client, alice, JLPT_APKG)
    assert response.status_code == 201, response.text
    return response.json()


class TestImport:
    def test_import_requires_auth(self, client):
        with RUSSIAN_APKG.open("rb") as handle:
            response = client.post(
                "/decks/import", files={"file": (RUSSIAN_APKG.name, handle)}
            )
        assert response.status_code == 401

    def test_import_small_deck(self, small_deck):
        deck = small_deck["deck"]
        assert deck["title"] == "10月20日"
        assert deck["total_items"] == 15
        assert deck["status"] == "draft"
        assert deck["package_version"] == 3
        assert deck["schema_version"] == 18
        report = small_deck["report"]
        assert report["total_notes"] == 16
        assert report["skipped"] == {"front_without_kanji": 1}

    def test_import_jlpt_deck(self, jlpt_deck):
        deck = jlpt_deck["deck"]
        assert deck["total_items"] == 1896
        assert deck["needs_review"] == 73
        assert deck["quiz_ready"] == 1823
        assert jlpt_deck["report"]["duplicates"] == 0
        assert jlpt_deck["report"]["plans"]["jlpt"]["reading"] == "Reading"

    def test_rejects_wrong_extension(self, client, alice):
        response = client.post(
            "/decks/import",
            headers=alice,
            files={"file": ("notes.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400

    def test_rejects_garbage(self, client, alice):
        response = client.post(
            "/decks/import",
            headers=alice,
            files={"file": ("bad.apkg", b"not a zip", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "valid" in response.json()["detail"].lower()

    def test_deck_list_is_owner_scoped(self, client, alice, bob, small_deck):
        alice_decks = client.get("/decks", headers=alice).json()
        bob_decks = client.get("/decks", headers=bob).json()
        assert any(deck["id"] == small_deck["deck"]["id"] for deck in alice_decks)
        assert all(deck["id"] != small_deck["deck"]["id"] for deck in bob_decks)

    def test_other_user_cannot_read_deck(self, client, bob, small_deck):
        response = client.get(f"/decks/{small_deck['deck']['id']}", headers=bob)
        assert response.status_code == 404


class TestEditing:
    def test_items_are_paginated(self, client, alice, jlpt_deck):
        deck_id = jlpt_deck["deck"]["id"]
        response = client.get(
            f"/decks/{deck_id}/items?page=2&page_size=25", headers=alice
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1896
        assert len(body["items"]) == 25
        assert body["items"][0]["position"] == 25

    def test_filter_review(self, client, alice, jlpt_deck):
        deck_id = jlpt_deck["deck"]["id"]
        body = client.get(
            f"/decks/{deck_id}/items?filter=review&page_size=200", headers=alice
        ).json()
        assert body["total"] == 73
        assert all(item["needs_review"] for item in body["items"])

    def test_search(self, client, alice, jlpt_deck):
        deck_id = jlpt_deck["deck"]["id"]
        body = client.get(
            f"/decks/{deck_id}/items?search=作法", headers=alice
        ).json()
        assert body["total"] == 1
        assert body["items"][0]["reading"] == "さほう"

    def test_edit_reading_and_meaning(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        items = client.get(f"/decks/{deck_id}/items?page_size=5", headers=alice).json()["items"]
        item = items[0]
        response = client.patch(
            f"/decks/{deck_id}/items/{item['id']}",
            headers=alice,
            json={"reading": "じせき", "meaning": "self-blame", "needs_review": False},
        )
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["meaning"] == "self-blame"
        assert updated["options"][updated["correct_index"]] == "じせき"

    def test_edit_reading_moves_the_correct_option(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        items = client.get(f"/decks/{deck_id}/items?page_size=5", headers=alice).json()["items"]
        item = items[0]
        original_options = item["options"]
        response = client.patch(
            f"/decks/{deck_id}/items/{item['id']}",
            headers=alice,
            json={"reading": "ひんかん"},
        )
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["reading"] == "ひんかん"
        assert updated["options"][updated["correct_index"]] == "ひんかん"
        assert len(updated["options"]) == len(original_options)
        assert "びんかん" not in updated["options"]

    def test_edit_options_cannot_conflict_with_reading(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        item = client.get(f"/decks/{deck_id}/items?page_size=1", headers=alice).json()["items"][0]
        response = client.patch(
            f"/decks/{deck_id}/items/{item['id']}",
            headers=alice,
            json={"options": ["むじゅん", "むしゅん", "むじゆん", "むじゅん"]},
        )
        assert response.status_code == 400

    def test_edit_options_valid(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        item = client.get(f"/decks/{deck_id}/items?page_size=1", headers=alice).json()["items"][0]
        reading = item["reading"]
        options = [reading, "あああ", "いいい", "ううう"]
        response = client.patch(
            f"/decks/{deck_id}/items/{item['id']}",
            headers=alice,
            json={"options": options, "correct_index": 2},
        )
        assert response.status_code == 200, response.text
        updated = response.json()
        assert updated["options"][updated["correct_index"]] == reading

    def test_rejects_kanji_reading(self, client, alice, small_deck):
        deck_id = small_deck["deck"]["id"]
        item = client.get(f"/decks/{deck_id}/items?page_size=1", headers=alice).json()["items"][0]
        response = client.patch(
            f"/decks/{deck_id}/items/{item['id']}",
            headers=alice,
            json={"reading": "自責"},
        )
        assert response.status_code == 400

    def test_bulk_update(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        items = client.get(f"/decks/{deck_id}/items?page_size=3", headers=alice).json()["items"]
        payload = {
            "updates": [
                [items[0]["id"], {"hidden": True}],
                [items[1]["id"], {"meaning": "bulk"}],
            ]
        }
        response = client.patch(
            f"/decks/{deck_id}/items", headers=alice, json=payload
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["items"][0]["hidden"] is True
        assert body["items"][1]["meaning"] == "bulk"

    def test_regenerate_options(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        item = client.get(f"/decks/{deck_id}/items?page_size=1", headers=alice).json()["items"][0]
        response = client.post(
            f"/decks/{deck_id}/items/{item['id']}/regenerate", headers=alice
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["options"][updated["correct_index"]] == updated["reading"]

    def test_add_and_delete_item(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        created = client.post(
            f"/decks/{deck_id}/items",
            headers=alice,
            json={"front": "経済", "reading": "けいざい", "meaning": "economy"},
        )
        assert created.status_code == 201, created.text
        item_id = created.json()["id"]
        assert len(created.json()["options"]) == 4

        deleted = client.delete(f"/decks/{deck_id}/items/{item_id}", headers=alice)
        assert deleted.status_code == 204

    def test_cannot_edit_foreign_item(self, client, bob, small_deck):
        deck_id = small_deck["deck"]["id"]
        response = client.patch(
            f"/decks/{deck_id}/items/1", headers=bob, json={"meaning": "hacked"}
        )
        assert response.status_code == 404

    def test_publish(self, client, alice, fresh_deck):
        deck_id = fresh_deck()["deck"]["id"]
        response = client.post(f"/decks/{deck_id}/publish", headers=alice)
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestQuiz:
    def test_start_requires_published_deck(self, client, alice):
        response = _upload(client, alice, JLPT_APKG, "unpublished.apkg")
        deck_id = response.json()["deck"]["id"]
        started = client.post(
            f"/decks/{deck_id}/sessions", headers=alice, json={"mode": "instant"}
        )
        assert started.status_code == 400

    def test_instant_flow(self, client, alice, small_deck):
        deck_id = small_deck["deck"]["id"]
        client.post(f"/decks/{deck_id}/publish", headers=alice)
        started = client.post(
            f"/decks/{deck_id}/sessions",
            headers=alice,
            json={"mode": "instant", "source": "all", "count": 3},
        )
        assert started.status_code == 201, started.text
        session = started.json()
        assert session["total"] == 3
        # The correct answer must not leak before answering.
        assert all(item["correct_index"] is None for item in session["items"])

        first = session["items"][0]
        response = client.post(
            f"/sessions/{session['id']}/answer",
            headers=alice,
            json={"item_id": first["id"], "selected_index": 1},
        )
        assert response.status_code == 200, response.text
        answer = response.json()
        assert answer["reading"]
        assert answer["correct_index"] in range(len(first["options"]))
        assert answer["item_id"] == first["id"]

        # Answer the rest, finish and inspect the results.
        for item in session["items"][1:]:
            client.post(
                f"/sessions/{session['id']}/answer",
                headers=alice,
                json={"item_id": item["id"], "selected_index": 0},
            )
        finished = client.post(f"/sessions/{session['id']}/finish", headers=alice)
        assert finished.status_code == 200
        result = finished.json()
        assert result["status"] == "finished"
        assert all(item["correct_index"] is not None for item in result["items"])
        assert result["correct"] == sum(1 for item in result["items"] if item["is_correct"])

        detail = client.get(f"/sessions/{session['id']}", headers=alice).json()
        assert detail["status"] == "finished"
        assert detail["answered"] == 3

    def test_end_flow_hides_answers_until_finish(self, client, alice, small_deck):
        deck_id = small_deck["deck"]["id"]
        client.post(f"/decks/{deck_id}/publish", headers=alice)
        started = client.post(
            f"/decks/{deck_id}/sessions",
            headers=alice,
            json={"mode": "end", "count": 4},
        )
        session = started.json()
        answers = [
            {"item_id": item["id"], "selected_index": index % len(item["options"])}
            for index, item in enumerate(session["items"])
        ]
        submitted = client.post(
            f"/sessions/{session['id']}/answers",
            headers=alice,
            json={"answers": answers},
        )
        assert submitted.status_code == 200, submitted.text
        # Mid-session state still hides the answers.
        assert all(item["correct_index"] is None for item in submitted.json()["items"])

        finished = client.post(f"/sessions/{session['id']}/finish", headers=alice)
        assert finished.status_code == 200
        assert all(item["correct_index"] is not None for item in finished.json()["items"])

    def test_retry_specific_items(self, client, alice, fresh_deck):
        deck = fresh_deck()["deck"]
        deck_id = deck["id"]
        client.post(f"/decks/{deck_id}/publish", headers=alice)

        first = client.post(
            f"/decks/{deck_id}/sessions", headers=alice, json={"mode": "end", "count": 4}
        ).json()
        answers = [
            {"item_id": item["id"], "selected_index": 0} for item in first["items"]
        ]
        client.post(
            f"/sessions/{first['id']}/answers", headers=alice, json={"answers": answers}
        )
        client.post(f"/sessions/{first['id']}/finish", headers=alice)
        result = client.get(f"/sessions/{first['id']}", headers=alice).json()
        wrong_ids = [item["item_id"] for item in result["items"] if item["is_correct"] is False]
        if not wrong_ids:
            wrong_ids = [result["items"][0]["item_id"]]

        retried = client.post(
            f"/decks/{deck_id}/sessions",
            headers=alice,
            json={"mode": "instant", "source": "all", "item_ids": wrong_ids},
        )
        assert retried.status_code == 201, retried.text
        assert retried.json()["total"] == len(wrong_ids)

    def test_cannot_mix_modes(self, client, alice, small_deck):
        deck_id = small_deck["deck"]["id"]
        session = client.post(
            f"/decks/{deck_id}/sessions", headers=alice, json={"mode": "end", "count": 1}
        ).json()
        response = client.post(
            f"/sessions/{session['id']}/answer",
            headers=alice,
            json={"item_id": session["items"][0]["id"], "selected_index": 0},
        )
        assert response.status_code == 400

    def test_cannot_finish_with_unanswered(self, client, alice, small_deck):
        deck_id = small_deck["deck"]["id"]
        session = client.post(
            f"/decks/{deck_id}/sessions", headers=alice, json={"mode": "end", "count": 2}
        ).json()
        response = client.post(f"/sessions/{session['id']}/finish", headers=alice)
        assert response.status_code == 400

    def test_statistics_after_finish(self, client, alice, small_deck):
        deck = client.get(f"/decks/{small_deck['deck']['id']}", headers=alice).json()["deck"]
        assert deck["sessions_completed"] >= 1
        assert deck["accuracy"] is not None
        assert deck["last_played_at"] is not None

    def test_session_is_owner_scoped(self, client, bob, small_deck, alice):
        deck_id = small_deck["deck"]["id"]
        session = client.post(
            f"/decks/{deck_id}/sessions", headers=alice, json={"mode": "end", "count": 1}
        ).json()
        assert client.get(f"/sessions/{session['id']}", headers=bob).status_code == 404
