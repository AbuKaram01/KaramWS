# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The command line."""

import io

import pytest

import karamws
from karamws import cli
from karamws.core import ScrapeEvent, ScrapeStatus


def test_the_version_is_reported(capsys):
    with pytest.raises(SystemExit) as stopped:
        cli.main(["--version"])
    assert stopped.value.code == 0
    assert capsys.readouterr().out.strip() == f"KaramWS {karamws.__version__}"


def test_a_link_is_required(capsys):
    with pytest.raises(SystemExit) as stopped:
        cli.main([])
    assert stopped.value.code == 2
    assert "url" in capsys.readouterr().err


def test_the_kind_has_to_be_one_the_program_knows(capsys):
    with pytest.raises(SystemExit):
        cli.main(["https://example.com/", "--kind", "galaxy"])
    assert "invalid choice" in capsys.readouterr().err


def test_a_console_that_cannot_show_arabic_letters_does_not_stop_the_program(monkeypatch):
    """A Windows pipe is cp1252: the name of a file saved from an Arabic title must not raise after it was saved."""
    pipe = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict", write_through=True)
    monkeypatch.setattr(cli.sys, "stdout", pipe)
    monkeypatch.setattr(cli.sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    cli._make_output_safe()
    event = ScrapeEvent(ScrapeStatus.SAVED, "https://موقع.مصر/مقال", "/home/me/مقال-one-1234567890.md")
    print(cli._describe(event), flush=True)
    written = pipe.buffer.getvalue().decode("ascii")
    assert "\\u0645" in written and "one-1234567890.md" in written


def test_output_is_left_alone_when_there_is_no_console(monkeypatch):
    monkeypatch.setattr(cli.sys, "stdout", None)
    monkeypatch.setattr(cli.sys, "stderr", None)
    cli._make_output_safe()  # pythonw has no streams: nothing to do, and no error
