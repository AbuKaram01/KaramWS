# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

from karamws.core.models import Article
from karamws.core.storage import ArticleStore


def make_article(url="https://site.com/a", title="Title", text="Body text"):
    return Article(url=url, title=title, text=text)


def test_arabic_titles_keep_their_letters_in_the_filename(tmp_path):
    path = ArticleStore(tmp_path).save(make_article(title="مراجعة هاتف: جديد!"))
    assert path.name.startswith("مراجعة-هاتف-جديد-")


def test_same_title_on_different_urls_does_not_overwrite(tmp_path):
    store = ArticleStore(tmp_path)
    first = store.save(make_article(url="https://site.com/1"))
    second = store.save(make_article(url="https://site.com/2"))
    assert first != second and first.exists() and second.exists()


def test_contains_recognises_only_saved_urls(tmp_path):
    store = ArticleStore(tmp_path)
    store.save(make_article(url="https://site.com/1"))
    assert store.contains("https://site.com/1")
    assert not store.contains("https://site.com/2")


def test_file_holds_title_source_and_text(tmp_path):
    path = ArticleStore(tmp_path).save(make_article(title="Hello", text="The body"))
    content = path.read_text(encoding="utf-8")
    assert content.startswith("# Hello")
    assert "- Source: https://site.com/a" in content
    assert "The body" in content


def test_title_without_usable_characters_falls_back_to_a_default_name(tmp_path):
    path = ArticleStore(tmp_path).save(make_article(title="!!!"))
    assert path.name.startswith("article-")
