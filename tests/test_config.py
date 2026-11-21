# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The saved settings."""

import json

import pytest

from karamws.config import (
    DEFAULT_HISTORY_LIMIT,
    MAX_HISTORY_LIMIT,
    MIN_HISTORY_LIMIT,
    AppConfig,
    config_file,
    update_saved_config,
)


def test_without_a_file_the_defaults_apply():
    config = AppConfig.load()
    assert config == AppConfig()
    assert config.respect_robots and config.notify_when_done and not config.welcome_done


def test_saved_settings_come_back():
    AppConfig(output_dir="/tmp/articles", max_articles=5, request_delay_seconds=2.5, notify_when_done=False).save()
    loaded = AppConfig.load()
    assert (loaded.output_dir, loaded.max_articles, loaded.request_delay_seconds) == ("/tmp/articles", 5, 2.5)
    assert loaded.notify_when_done is False


def test_arabic_text_is_saved_readably():
    AppConfig(output_dir="/home/محمد/Articles").save()
    assert "محمد" in config_file().read_text(encoding="utf-8")
    assert AppConfig.load().output_dir == "/home/محمد/Articles"


def test_a_field_of_the_wrong_kind_falls_back_to_its_default_and_the_rest_is_kept():
    config_file().parent.mkdir(parents=True)
    config_file().write_text(json.dumps({"max_articles": "many", "respect_robots": 1, "output_dir": "/x"}))
    loaded = AppConfig.load()
    assert loaded.max_articles == 0 and loaded.respect_robots is True  # a bool field refuses an int
    assert loaded.output_dir == "/x"


def test_a_file_that_is_not_an_object_is_set_aside_not_overwritten():
    config_file().parent.mkdir(parents=True)
    config_file().write_text("[1, 2, 3]")
    assert AppConfig.load() == AppConfig()
    assert config_file().with_name("config.json.broken").read_text() == "[1, 2, 3]"


def test_an_unknown_key_in_the_file_is_ignored():
    config_file().parent.mkdir(parents=True)
    config_file().write_text(json.dumps({"colour": "red", "max_articles": 3}))
    assert AppConfig.load().max_articles == 3


def test_updating_re_reads_the_file_so_that_other_changes_survive():
    AppConfig(max_articles=7).save()
    update_saved_config(notify_when_done=False)
    loaded = AppConfig.load()
    assert loaded.max_articles == 7 and loaded.notify_when_done is False


def test_updating_a_setting_that_does_not_exist_is_a_bug():
    with pytest.raises(AttributeError):
        update_saved_config(colour="red")


def test_the_engine_is_told_what_the_settings_say():
    scraper = AppConfig(max_articles=12, request_delay_seconds=0.5, respect_robots=False,
                        use_browser_fallback=False).scraper_config()
    assert (scraper.max_articles, scraper.request_delay_seconds) == (12, 0.5)
    assert scraper.respect_robots is False and scraper.use_browser_fallback is False
    assert AppConfig(max_articles=0).scraper_config().max_articles is None  # 0 means no limit


def test_the_history_limit_is_kept_in_its_range():
    assert AppConfig().history_keep == DEFAULT_HISTORY_LIMIT
    assert AppConfig(history_limit=-5).history_keep == MIN_HISTORY_LIMIT
    assert AppConfig(history_limit=10**9).history_keep == MAX_HISTORY_LIMIT
