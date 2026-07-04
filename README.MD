# codex-accounts

English | [简体中文](README.zh-CN.md) | [Changelog](CHANGELOG.md)

`codex-accounts` switches between multiple Codex account directories by keeping each account in `~/.codex-<name>` and pointing the active `~/.codex` path at the selected account.

The project now has two entry points:

- A cross-platform Python 3 CLI for Linux, macOS, and Windows.
- The original macOS Bash script, still kept at [`codex-accounts`](codex-accounts), for users who installed the shell workflow directly.

On macOS, the Python CLI preserves the original app workflow: stop Codex App, switch the account link, and start Codex App again. On Linux and Windows, app control is skipped and the CLI only switches the account link.

## Features

- Manage account directories such as `~/.codex-work` and `~/.codex-personal`.
- Switch the active `~/.codex` symlink or directory link.
- Create account directories and migrate an existing real `~/.codex` directory.
- Keep macOS Codex App stop/start/restart support.
- Block unsafe operations from a detected Codex built-in terminal when they cannot be delegated safely.
- Support English and Chinese output through `CODEX_ACCOUNTS_LANG`.
- Package as a Python project with tests, CI, and PyPI publishing workflow.

## Requirements

- Python 3.9 or newer for the Python CLI.
- macOS is required only for Codex App control commands: `start`, `stop`, and `restart`.
- Linux and macOS use directory symlinks.
- Windows uses directory symlinks when available and falls back to directory junctions.

## Install

Install the Python CLI from PyPI:

```bash
python3 -m pip install codex-accounts
```

For isolated CLI installs, `pipx` is recommended:

```bash
pipx install codex-accounts
```

Install from a local checkout for development:

```bash
python3 -m pip install -e ".[dev]"
```

The legacy macOS shell installer is still available:

```bash
tmp="$(mktemp -t codex-accounts.XXXXXX)" && curl -fsSL https://raw.githubusercontent.com/blockchain-project-lives/codex-accounts/main/codex-accounts -o "$tmp" && bash "$tmp" install && rm -f "$tmp"
```

## Account Layout

Default layout:

```text
~/.codex           -> active account link
~/.codex-work      account directory named work
~/.codex-personal  account directory named personal
```

Customize paths with `CODEX_ACCOUNTS_LINK` and `CODEX_ACCOUNTS_PREFIX`.

## Usage

Create accounts:

```bash
codex-accounts create personal
codex-accounts create work
```

If you already have a real `~/.codex` directory, migrate it first:

```bash
codex-accounts create personal --migrate-current
```

Switch accounts:

```bash
codex-accounts work
codex-accounts use personal
codex-accounts switch work
```

On macOS, switching stops and restarts Codex App by default. Skip those steps when needed:

```bash
codex-accounts work --no-stop --no-start
```

Inspect accounts:

```bash
codex-accounts list
codex-accounts current
```

Control Codex App on macOS:

```bash
codex-accounts stop
codex-accounts start
codex-accounts restart
```

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `CODEX_APP_NAME` | `Codex` | macOS app name to control. |
| `CODEX_QUIT_TIMEOUT` | `20` | Seconds to wait for app exit. |
| `CODEX_ACCOUNTS_LINK` | `$HOME/.codex` | Active account link path. |
| `CODEX_ACCOUNTS_PREFIX` | `$HOME/.codex-` | Account directory prefix. |
| `CODEX_ACCOUNTS_LANG` | auto | Force output language with `en` or `zh`. |

Legacy aliases `CODEX_ACCOUNT_LINK`, `CODEX_ACCOUNT_PREFIX`, and `CODEX_ACCOUNT_LANG` are still honored.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
```

Design, test, and release notes live in [`docs/`](docs/).

## Publishing

CI runs tests on Linux, macOS, and Windows across Python 3.9, 3.11, and 3.13. The `Publish to PyPI` workflow builds and publishes distributions when a GitHub Release is published or the workflow is run manually.

Configure TestPyPI and PyPI Trusted Publishing for this repository before using the release workflows. See [`docs/RELEASE.zh-CN.md`](docs/RELEASE.zh-CN.md).
