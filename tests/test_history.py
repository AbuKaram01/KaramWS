# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The history of the jobs that ended."""

import json

from karamws.core.history import HistoryStore, new_entry


def entry(url: str, saved: int = 1, outcome: str = "done"):
    return new_entry(url, "auto", "/tmp/out", saved, 0, 0, outcome)


def test_a_new_history_is_empty(tmp_path):
    assert HistoryStore(tmp_path / "history.json").entries() == []


def test_entries_come_back_newest_first(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    first, second = entry("https://a.com/"), entry("https://b.com/")
    object.__setattr__(first, "started_at", "2026-01-01T10:00:00+00:00")
    object.__setattr__(second, "started_at", "2026-01-02T10:00:00+00:00")
    store.add(first, keep=10)
    store.add(second, keep=10)
    assert [e.url for e in store.entries()] == ["https://b.com/", "https://a.com/"]


def test_only_the_newest_entries_are_kept(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    for number in range(5):
        item = entry(f"https://site.com/{number}")
        object.__setattr__(item, "started_at", f"2026-01-0{number + 1}T00:00:00+00:00")
        store.add(item, keep=3)
    assert [e.url for e in store.entries()] == [f"https://site.com/{n}" for n in (4, 3, 2)]


def test_one_entry_can_be_deleted_and_all_can_be_cleared(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    keep, drop = entry("https://keep.com/"), entry("https://drop.com/")
    store.add(keep, keep=10)
    store.add(drop, keep=10)
    store.delete(drop.id)
    assert [e.url for e in store.entries()] == ["https://keep.com/"]
    store.clear()
    assert store.entries() == []


def test_a_damaged_file_is_set_aside_and_gives_an_empty_history(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{not json")
    assert HistoryStore(path).entries() == []
    assert (tmp_path / "history.json.broken").read_text() == "{not json"


def test_entries_that_are_not_valid_are_skipped(tmp_path):
    path = tmp_path / "history.json"
    good = entry("https://ok.com/")
    path.write_text(json.dumps([good.__dict__, {"id": 1}, "nonsense", {**good.__dict__, "saved": "many"}]))
    assert [e.id for e in HistoryStore(path).entries()] == [good.id]


def test_arabic_urls_and_folders_survive(tmp_path):
    store = HistoryStore(tmp_path / "history.json")
    store.add(new_entry("https://موقع.مصر/مقال", "article", "/home/محمد/Articles", 1, 0, 0, "done"), keep=5)
    assert store.entries()[0].output_dir == "/home/محمد/Articles"
