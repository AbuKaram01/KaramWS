# SPDX-FileCopyrightText: 2026 AbuKaram01
# SPDX-License-Identifier: AGPL-3.0-or-later

"""The command line."""

import pytest

import karamws
from karamws import cli


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
