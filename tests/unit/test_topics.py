"""Unit tests for topic/entry storage in data_storage."""

import json

import pytest

from src import data_storage


@pytest.fixture
def temp_data_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(data_storage, "get_data_dir", lambda: tmp_path)
    return tmp_path


def test_get_topics_empty(temp_data_dir):
    assert data_storage.get_topics() == {}


def test_add_topic_and_entries(temp_data_dir):
    assert data_storage.add_topic("git") is True
    assert data_storage.add_topic("git") is False  # duplicate
    assert data_storage.add_topic("   ") is False  # blank

    assert data_storage.add_topic_entry("git", "compare to origin main", "git diff origin/main\nmulti\nline") is True
    assert data_storage.add_topic_entry("nope", "k", "v") is False  # missing topic

    topics = data_storage.get_topics()
    assert topics["git"] == [{"key": "compare to origin main", "value": "git diff origin/main\nmulti\nline"}]


def test_update_and_delete_entry(temp_data_dir):
    data_storage.add_topic("git")
    data_storage.add_topic_entry("git", "a", "1")
    data_storage.add_topic_entry("git", "b", "2")

    assert data_storage.update_topic_entry("git", 1, "b2", "22") is True
    assert data_storage.update_topic_entry("git", 9, "x", "y") is False  # out of range
    assert data_storage.update_topic_entry("nope", 0, "x", "y") is False

    assert data_storage.get_topics()["git"][1] == {"key": "b2", "value": "22"}

    assert data_storage.delete_topic_entry("git", 0) is True
    assert data_storage.delete_topic_entry("git", 5) is False
    assert len(data_storage.get_topics()["git"]) == 1


def test_delete_topic(temp_data_dir):
    data_storage.add_topic("git")
    data_storage.add_topic_entry("git", "k", "v")

    assert data_storage.delete_topic("git") is True
    assert data_storage.delete_topic("git") is False
    assert data_storage.get_topics() == {}


def test_topics_file_format(temp_data_dir):
    data_storage.add_topic("git")
    data_storage.add_topic_entry("git", "k", "v")

    raw = json.loads((temp_data_dir / "topics.json").read_text())
    assert raw == {"topics": {"git": [{"key": "k", "value": "v"}]}}


def test_corrupt_topics_file(temp_data_dir):
    (temp_data_dir / "topics.json").write_text("not json")
    assert data_storage.get_topics() == {}
