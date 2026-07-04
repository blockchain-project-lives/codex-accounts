from __future__ import annotations

import io
from pathlib import Path

import pytest

from codex_accounts.config import Config
from codex_accounts.cli import run
from codex_accounts.core import AccountManager
from codex_accounts.errors import CodexAccountsError
from test_core import FakePlatform


def manager_for(tmp_path: Path) -> AccountManager:
    home = tmp_path / "home"
    home.mkdir()
    config = Config(
        app_name="Codex",
        home_dir=home,
        active_link=home / ".codex",
        account_prefix=str(home / ".codex-"),
        quit_timeout=20,
        lang="en",
    )
    return AccountManager(config, FakePlatform(), io.StringIO(), io.StringIO())


class TestCliDispatch:
    def test_create_and_account_name_alias(self, tmp_path: Path) -> None:
        manager = manager_for(tmp_path)

        assert run(["create", "work"], manager) == 0
        assert run(["work", "--no-stop", "--no-start"], manager) == 0

        assert manager.current_target().kind == "target"

    def test_current_returns_named_account(self, tmp_path: Path) -> None:
        manager = manager_for(tmp_path)

        run(["create", "work"], manager)
        run(["switch", "work", "--no-stop", "--no-start"], manager)
        assert run(["current"], manager) == 0

        assert "work ->" in manager.stdout.getvalue()

    def test_unknown_command_raises_expected_error(self, tmp_path: Path) -> None:
        manager = manager_for(tmp_path)

        with pytest.raises(CodexAccountsError, match="Unknown command"):
            run(["missing"], manager)

    def test_help_prints_usage(self, tmp_path: Path) -> None:
        manager = manager_for(tmp_path)

        assert run(["help"], manager) == 0

        assert "Codex multi-account switcher" in manager.stdout.getvalue()
