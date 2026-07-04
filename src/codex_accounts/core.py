from __future__ import annotations

import glob
import os
import re
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, TextIO

from .config import Config
from .errors import CodexAccountsError
from .platforms import SystemPlatform

ACCOUNT_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def strip_account_name(value: str) -> str:
    name = re.split(r"[\\/]+", value.rstrip("\\/"))[-1]
    if name.startswith(".codex-"):
        name = name[len(".codex-") :]
    return name


def validate_account_name(name: str) -> None:
    if not name:
        raise CodexAccountsError("Account name cannot be empty")
    if name in {".", ".."}:
        raise CodexAccountsError(f"Account name cannot be {name}")
    if not ACCOUNT_RE.match(name):
        raise CodexAccountsError(
            "Account name can only contain letters, numbers, dots, underscores, and hyphens: "
            + name
        )


def account_dir(config: Config, name: str) -> Path:
    clean_name = strip_account_name(name)
    validate_account_name(clean_name)
    return Path(config.account_prefix + clean_name)


@dataclass(frozen=True)
class CurrentTarget:
    kind: str
    path: Optional[Path] = None


class AccountManager:
    def __init__(
        self,
        config: Config,
        platform_service: Optional[SystemPlatform] = None,
        stdout: Optional[TextIO] = None,
        stderr: Optional[TextIO] = None,
    ) -> None:
        self.config = config
        self.platform = platform_service or SystemPlatform()
        self.stdout = stdout or sys.stdout
        self.stderr = stderr or sys.stderr

    def is_zh(self) -> bool:
        return self.config.lang == "zh"

    def message(self, zh: str, en: str) -> str:
        return zh if self.is_zh() else en

    def fail(self, zh: str, en: str) -> None:
        raise CodexAccountsError(self.message(zh, en))

    def info(self, text: str = "") -> None:
        print(text, file=self.stdout)

    def bold(self, text: str) -> str:
        isatty = getattr(self.stdout, "isatty", lambda: False)
        return f"\033[1m{text}\033[0m" if isatty() else text

    def account_dir(self, name: str) -> Path:
        return account_dir(self.config, name)

    def real_dir(self, path: Path) -> Path:
        if self.platform.is_directory_link(path):
            return path.resolve(strict=False)
        if path.is_dir():
            return path.resolve(strict=True)
        return path

    def current_target(self) -> CurrentTarget:
        active = self.config.active_link
        if self.platform.is_directory_link(active):
            return CurrentTarget("target", self.real_dir(active))
        if active.exists():
            return CurrentTarget("not-a-link", active)
        return CurrentTarget("missing")

    def account_dirs(self) -> List[Path]:
        dirs = [Path(path) for path in glob.glob(self.config.account_prefix + "*")]
        return sorted(path for path in dirs if path.is_dir())

    def same_path(self, left: Path, right: Path) -> bool:
        left_s = os.path.normcase(os.path.abspath(left))
        right_s = os.path.normcase(os.path.abspath(right))
        return left_s == right_s

    def current_name(self, target: Path) -> Optional[str]:
        for directory in self.account_dirs():
            if self.same_path(self.real_dir(directory), target):
                return strip_account_name(str(directory))
        return None

    def list_accounts(self) -> None:
        current = self.current_target()
        self.info(self.bold(self.message("Codex 账号", "Codex accounts")))
        found = False
        for directory in self.account_dirs():
            found = True
            name = strip_account_name(str(directory))
            marker = " "
            if current.kind == "target" and current.path:
                marker = "*" if self.same_path(self.real_dir(directory), current.path) else " "
            self.info(f" {marker} {name:<16} {directory}")

        if not found:
            self.info(
                self.message(
                    "未找到账号目录。可以先执行: codex-accounts create work",
                    "No account directories found. You can create one with: codex-accounts create work",
                )
            )

        self.info()
        if current.kind == "missing":
            self.info(
                self.message(
                    f"当前 {self.config.active_link} 不存在。",
                    f"Current {self.config.active_link} does not exist.",
                )
            )
        elif current.kind == "not-a-link":
            self.info(
                self.message(
                    f"当前 {self.config.active_link} 存在，但不是软链接，切换前需要手动处理。",
                    f"Current {self.config.active_link} exists, but it is not a symlink. Please handle it manually before switching.",
                )
            )
        elif current.path:
            name = self.current_name(current.path)
            if name:
                self.info(
                    self.message(
                        f"当前账号: {name} -> {current.path}",
                        f"Current account: {name} -> {current.path}",
                    )
                )
            else:
                self.info(
                    self.message(
                        f"当前账号: 未匹配到账号目录 -> {current.path}",
                        f"Current account: no matching account directory -> {current.path}",
                    )
                )

    def show_current(self) -> None:
        current = self.current_target()
        if current.kind == "missing":
            self.fail(
                f"{self.config.active_link} 不存在",
                f"{self.config.active_link} does not exist",
            )
        if current.kind == "not-a-link":
            self.fail(
                f"{self.config.active_link} 存在，但不是软链接",
                f"{self.config.active_link} exists, but it is not a symlink",
            )
        assert current.path is not None
        name = self.current_name(current.path) or "unknown"
        self.info(f"{name} -> {current.path}")

    def stop_codex(self, force: bool = False, argv: Optional[Sequence[str]] = None) -> None:
        if self.platform.is_codex_terminal():
            if self.platform.supports_external_terminal_delegation:
                self.platform.delegate_to_external_terminal(
                    self.config,
                    self.message("关闭 Codex", "stop Codex"),
                    list(argv or (["stop", "--force"] if force else ["stop"])),
                    self.stdout,
                )
                return
            self.require_external_terminal("stop")

        if not self.platform.supports_app_control:
            self.fail(
                "当前平台不支持自动关闭 Codex App。切换账号时可使用 --no-stop。",
                "App stop is only supported on macOS. Use --no-stop when switching accounts on this platform.",
            )
        self.platform.stop_app(
            self.config.app_name,
            self.config.quit_timeout,
            force,
            self.stdout,
        )

    def start_codex(self) -> None:
        self.require_external_terminal("start")
        if not self.platform.supports_app_control:
            self.fail(
                "当前平台不支持自动启动 Codex App。",
                "App start is only supported on macOS.",
            )
        self.info(self.message(f"正在启动 {self.config.app_name} ...", f"Starting {self.config.app_name} ..."))
        self.platform.start_app(self.config.app_name)

    def restart_codex(self, force: bool = False, argv: Optional[Sequence[str]] = None) -> None:
        if self.platform.is_codex_terminal():
            if self.platform.supports_external_terminal_delegation:
                self.platform.delegate_to_external_terminal(
                    self.config,
                    self.message("重启 Codex", "restart Codex"),
                    list(argv or (["restart", "--force"] if force else ["restart"])),
                    self.stdout,
                )
                return
            self.require_external_terminal("restart")
        self.stop_codex(force)
        self.start_codex()

    def require_external_terminal(self, action: str) -> None:
        if not self.platform.is_codex_terminal():
            return
        zh_actions = {
            "stop": "关闭 Codex",
            "start": "启动 Codex",
            "restart": "重启 Codex",
            "switch": "切换账号",
            "migration": "迁移账号目录",
        }
        self.fail(
            f"不能在 Codex 内置 Terminal 中执行{zh_actions.get(action, action)}。请打开外部系统 Terminal，在 Codex 外部运行该命令。",
            f"Cannot run {action} from the built-in Codex terminal. Open an external system Terminal and run this command outside Codex.",
        )

    def ensure_app_not_running_for_migration(self) -> None:
        status = self.platform.app_running_status(self.config.app_name)
        if status is True:
            self.fail(
                f"{self.config.app_name} 正在运行。为避免配置损坏，请先从外部 Terminal 关闭 {self.config.app_name} 后再执行迁移。",
                f"{self.config.app_name} is running. To avoid corrupting config files, quit {self.config.app_name} from an external terminal before migration.",
            )
        if status is None and self.platform.supports_app_control:
            self.fail(
                f"无法确认 {self.config.app_name} 是否运行。为避免配置损坏，请先从外部 Terminal 确认 {self.config.app_name} 已关闭后再执行迁移。",
                f"Cannot confirm whether {self.config.app_name} is running. To avoid corrupting config files, confirm {self.config.app_name} is closed from an external terminal before migration.",
            )

    def switch_account(self, name: str, args: Sequence[str], original_argv: Sequence[str]) -> None:
        stop_first = True
        start_after = True
        force = False
        for arg in args:
            if arg == "--no-stop":
                stop_first = False
            elif arg == "--no-start":
                start_after = False
            elif arg in {"--force", "-f"}:
                force = True
            elif arg in {"-h", "--help"}:
                self.info(usage(self.config.lang))
                return
            else:
                self.fail(f"未知参数: {arg}", f"Unknown option: {arg}")

        if self.platform.is_codex_terminal():
            if self.platform.supports_external_terminal_delegation:
                self.platform.delegate_to_external_terminal(
                    self.config,
                    self.message("切换账号", "switch accounts"),
                    original_argv,
                    self.stdout,
                )
                return
            self.require_external_terminal("switch")

        clean_name = strip_account_name(name)
        validate_account_name(clean_name)
        directory = self.account_dir(clean_name)
        if not directory.is_dir():
            self.fail(
                f"账号不存在: {directory}。可先执行: codex-accounts create {clean_name}",
                f"Account does not exist: {directory}. You can create it with: codex-accounts create {clean_name}",
            )

        active = self.config.active_link
        if active.exists() and not self.platform.is_directory_link(active):
            self.fail(
                f"{active} 已存在但不是软链接。为避免误删，请先手动备份/迁移它。",
                f"{active} already exists but is not a symlink. Please back it up or migrate it manually before switching.",
            )

        if stop_first:
            if self.platform.supports_app_control:
                self.stop_codex(force)
            else:
                self.info(
                    self.message(
                        "当前平台不支持自动关闭 Codex App，继续只切换账号链接。",
                        "App stop is not supported on this platform; continuing with the account link switch.",
                    )
                )

        active.parent.mkdir(parents=True, exist_ok=True)
        if self.platform.is_directory_link(active):
            self.platform.remove_directory_link(active)
        self.platform.create_directory_link(directory, active)
        self.info(self.message(f"已切换到: {clean_name} -> {directory}", f"Switched to: {clean_name} -> {directory}"))

        if start_after:
            if self.platform.supports_app_control:
                self.start_codex()
            else:
                self.info(
                    self.message(
                        "当前平台不支持自动启动 Codex App，账号链接已完成切换。",
                        "App start is not supported on this platform; the account link has been switched.",
                    )
                )

    def create_account(self, name: str, args: Sequence[str]) -> None:
        migrate_current = False
        for arg in args:
            if arg in {"--migrate-current", "--migrate"}:
                migrate_current = True
            elif arg in {"-h", "--help"}:
                self.info(usage(self.config.lang))
                return
            else:
                self.fail(f"未知参数: {arg}", f"Unknown option: {arg}")

        if not name:
            self.fail(
                "缺少账号名，例如: codex-accounts create work",
                "Missing account name, for example: codex-accounts create work",
            )

        clean_name = strip_account_name(name)
        validate_account_name(clean_name)
        directory = self.account_dir(clean_name)
        if directory.exists():
            self.fail(f"账号目录已存在: {directory}", f"Account directory already exists: {directory}")

        if migrate_current:
            self.require_external_terminal("migration")
            self.ensure_app_not_running_for_migration()
            active = self.config.active_link
            if self.platform.is_directory_link(active):
                self.fail(
                    f"{active} 已经是软链接，无需迁移。",
                    f"{active} is already a symlink; there is nothing to migrate.",
                )
            if not active.exists():
                self.fail(f"{active} 不存在，无法迁移。", f"{active} does not exist, so it cannot be migrated.")
            if not active.is_dir():
                self.fail(
                    f"{active} 存在但不是目录，无法迁移。",
                    f"{active} exists but is not a directory, so it cannot be migrated.",
                )
            directory.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(active), str(directory))
            self.platform.create_directory_link(directory, active)
            self.info(self.message(f"已迁移当前账号: {active} -> {directory}", f"Migrated current account: {active} -> {directory}"))
            return

        directory.mkdir(parents=True, exist_ok=False)
        self.info(self.message(f"已创建账号目录: {directory}", f"Created account directory: {directory}"))

    def install_self(self, destination: Optional[str] = None) -> None:
        dest = Path(destination) if destination else self.default_install_dir()
        if dest is None:
            self.fail(
                "无法判断安装目录，请指定，例如: codex-accounts install /usr/local/bin",
                "Could not choose an install directory. Please specify one, for example: codex-accounts install /usr/local/bin",
            )
        dest.mkdir(parents=True, exist_ok=True)
        if self.platform.is_windows:
            launcher = dest / "codex-accounts.cmd"
            launcher.write_text(
                f'@echo off\r\n"{sys.executable}" -m codex_accounts %*\r\n',
                encoding="utf-8",
            )
        else:
            launcher = dest / "codex-accounts"
            launcher.write_text(
                "#!/usr/bin/env sh\n"
                f"exec {shlex.quote(sys.executable)} -m codex_accounts \"$@\"\n",
                encoding="utf-8",
            )
            launcher.chmod(0o755)
        self.info(self.message(f"已安装: {launcher}", f"Installed: {launcher}"))

        if not self.path_contains_dir(dest):
            self.info(
                self.message(
                    f"提醒: {dest} 目前不在 PATH 中，需要加入 shell 配置。",
                    f"Note: {dest} is not currently in PATH. Add it to your shell config before using the command directly.",
                )
            )

    def path_contains_dir(self, directory: Path) -> bool:
        path_parts = os.environ.get("PATH", "").split(os.pathsep)
        target = os.path.normcase(os.path.abspath(directory))
        return any(os.path.normcase(os.path.abspath(part or ".")) == target for part in path_parts)

    def default_install_dir(self) -> Optional[Path]:
        candidates: Iterable[Path]
        if self.platform.is_windows:
            candidates = [
                self.config.home_dir / "AppData" / "Roaming" / "Python" / "Scripts",
                self.config.home_dir / ".local" / "bin",
            ]
        else:
            candidates = [
                self.config.home_dir / ".local" / "bin",
                self.config.home_dir / "bin",
                Path("/opt/homebrew/bin"),
                Path("/usr/local/bin"),
            ]
        for directory in candidates:
            if self.path_contains_dir(directory) and directory.is_dir() and os.access(directory, os.W_OK):
                return directory
        for directory in candidates:
            if self.path_contains_dir(directory) or directory == self.config.home_dir / ".local" / "bin":
                return directory
        return None


def usage(lang: str) -> str:
    if lang == "zh":
        return """codex-accounts - Codex 多账号切换工具

账号约定:
  当前账号: ~/.codex                 软链接/目录链接
  账号目录: ~/.codex-work            账号名 work
            ~/.codex-personal        账号名 personal

用法:
  codex-accounts list | ls
      查看所有账号目录，并标出当前账号。

  codex-accounts current
      显示当前 ~/.codex 指向哪个账号。

  codex-accounts use <账号名> [--no-stop] [--no-start] [--force]
  codex-accounts switch <账号名> [--no-stop] [--no-start] [--force]
  codex-accounts <账号名>
      切换 ~/.codex 链接到指定账号目录。
      macOS 上默认会关闭 Codex App、切换账号、再启动 Codex App。
      Linux/Windows 上会跳过 App 启停，只切换账号链接。

  codex-accounts stop [--force]
      关闭 Codex App。当前仅支持 macOS。

  codex-accounts start
      启动 Codex App。当前仅支持 macOS。

  codex-accounts restart [--force]
      重启 Codex App。当前仅支持 macOS。

  codex-accounts create <账号名> [--migrate-current]
      创建新的账号目录 ~/.codex-<账号名>。
      加 --migrate-current 可将已有的真实 ~/.codex 目录迁移为该账号。

  codex-accounts install [目录]
      安装 Python 启动器到 PATH 目录。推荐优先使用 pipx 或 pip 安装。

  codex-accounts help
      显示帮助。

环境变量:
  CODEX_APP_NAME        App 名称，默认 Codex
  CODEX_QUIT_TIMEOUT    等待 App 退出秒数，默认 20
  CODEX_ACCOUNTS_LINK   当前账号链接，默认 ~/.codex
  CODEX_ACCOUNTS_PREFIX 账号目录前缀，默认 ~/.codex-
  CODEX_ACCOUNTS_LANG   强制提示语言，可设为 zh 或 en
  兼容旧变量: CODEX_ACCOUNT_LINK / CODEX_ACCOUNT_PREFIX / CODEX_ACCOUNT_LANG"""

    return """codex-accounts - Codex multi-account switcher

Account layout:
  Active account: ~/.codex                 symlink/directory link
  Account dirs:   ~/.codex-work            account name: work
                  ~/.codex-personal        account name: personal

Usage:
  codex-accounts list | ls
      List all account directories and mark the active account.

  codex-accounts current
      Show where ~/.codex currently points.

  codex-accounts use <account> [--no-stop] [--no-start] [--force]
  codex-accounts switch <account> [--no-stop] [--no-start] [--force]
  codex-accounts <account>
      Switch the ~/.codex link to the selected account directory.
      On macOS this quits Codex App, switches the account, then starts Codex App.
      On Linux and Windows app control is skipped and only the account link changes.

  codex-accounts stop [--force]
      Quit Codex App. Currently supported on macOS only.

  codex-accounts start
      Start Codex App. Currently supported on macOS only.

  codex-accounts restart [--force]
      Restart Codex App. Currently supported on macOS only.

  codex-accounts create <account> [--migrate-current]
      Create a new account directory ~/.codex-<account>.
      Add --migrate-current to migrate an existing real ~/.codex directory.

  codex-accounts install [directory]
      Install a Python launcher into a PATH directory. pipx or pip is preferred.

  codex-accounts help
      Show this help.

Environment variables:
  CODEX_APP_NAME        App name, default: Codex
  CODEX_QUIT_TIMEOUT    Seconds to wait for app exit, default: 20
  CODEX_ACCOUNTS_LINK   Active account link, default: ~/.codex
  CODEX_ACCOUNTS_PREFIX Account directory prefix, default: ~/.codex-
  CODEX_ACCOUNTS_LANG   Force output language: zh or en
  Legacy aliases: CODEX_ACCOUNT_LINK / CODEX_ACCOUNT_PREFIX / CODEX_ACCOUNT_LANG"""
