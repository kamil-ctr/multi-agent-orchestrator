from __future__ import annotations

import pytest

from core.conversations import ConversationStore


@pytest.fixture
def store(tmp_path):
    return ConversationStore(tmp_path / "conversations.sqlite")


def test_create_and_get_meta(store):
    conv_id = store.create(title="Hello world")
    meta = store.get_meta(conv_id)

    assert meta["id"] == conv_id
    assert meta["title"] == "Hello world"
    assert meta["message_count"] == 0


def test_create_default_title(store):
    conv_id = store.create()
    meta = store.get_meta(conv_id)
    assert meta["title"] == "New conversation"


def test_add_message_bumps_updated_at_and_count(store):
    conv_id = store.create()
    before = store.get_meta(conv_id)["updated_at"]

    store.add_message(conv_id, role="user", content="hi")
    after = store.get_meta(conv_id)

    assert after["message_count"] == 1
    assert after["updated_at"] >= before


def test_get_returns_messages_in_order_with_parsed_agent_responses(store):
    conv_id = store.create()
    store.add_message(conv_id, role="user", content="What is 2+2?")
    store.add_message(conv_id, role="assistant", content="4", agent_responses_json='{"foo": "bar"}')

    conv = store.get(conv_id)

    assert conv["id"] == conv_id
    assert len(conv["messages"]) == 2
    assert conv["messages"][0]["role"] == "user"
    assert conv["messages"][0]["agent_responses"] is None
    assert conv["messages"][1]["role"] == "assistant"
    assert conv["messages"][1]["agent_responses"] == {"foo": "bar"}


def test_get_missing_conversation_returns_none(store):
    assert store.get(999) is None


def test_list_orders_by_updated_at_desc_and_supports_search(store):
    a = store.create(title="Alpha topic")
    b = store.create(title="Beta topic")
    store.add_message(a, role="user", content="hi")  # bumps a's updated_at to be newest

    items = store.list()
    assert [i["id"] for i in items] == [a, b]

    filtered = store.list(search="Beta")
    assert [i["id"] for i in filtered] == [b]


def test_rename(store):
    conv_id = store.create(title="Old title")
    store.rename(conv_id, "New title")
    assert store.get_meta(conv_id)["title"] == "New title"


def test_delete_removes_conversation_and_messages(store):
    conv_id = store.create()
    store.add_message(conv_id, role="user", content="hi")

    store.delete(conv_id)

    assert store.get_meta(conv_id) is None
    assert store.exists(conv_id) is False


def test_exists(store):
    conv_id = store.create()
    assert store.exists(conv_id) is True
    assert store.exists(conv_id + 999) is False


def test_build_context_formats_messages_oldest_first(store):
    conv_id = store.create()
    store.add_message(conv_id, role="user", content="first question")
    store.add_message(conv_id, role="assistant", content="first answer")
    store.add_message(conv_id, role="user", content="second question")

    context = store.build_context(conv_id, max_messages=10, max_tokens=3000)

    lines = context.split("\n")
    assert lines[0] == "User: first question"
    assert lines[1] == "Assistant: first answer"
    assert lines[2] == "User: second question"


def test_build_context_empty_for_fresh_conversation(store):
    conv_id = store.create()
    assert store.build_context(conv_id) == ""


def test_build_context_respects_max_messages(store):
    conv_id = store.create()
    for i in range(5):
        store.add_message(conv_id, role="user", content=f"message {i}")

    context = store.build_context(conv_id, max_messages=2, max_tokens=3000)

    lines = context.split("\n")
    assert len(lines) == 2
    assert lines[0] == "User: message 3"
    assert lines[1] == "User: message 4"


def test_build_context_trims_oldest_when_over_token_budget(store):
    conv_id = store.create()
    store.add_message(conv_id, role="user", content="x" * 400)  # ~100 tokens
    store.add_message(conv_id, role="user", content="short")

    context = store.build_context(conv_id, max_messages=10, max_tokens=10)

    assert "x" * 400 not in context
    assert "short" in context
