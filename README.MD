# codex-workspaces

English | [简体中文](README.zh-CN.md) | [Changelog](CHANGELOG.md)

`codex-workspaces` switches between multiple Codex workspace directories under `~/.codex-workspaces/workspaces/` and points the active `~/.codex` path at the selected workspace.

The project now has two entry points:

- A cross-platform Python 3 CLI for Linux, macOS, and Windows.
- The original macOS Bash script, still kept at [`macos/codex-workspaces`](macos/codex-workspaces), for users who installed the shell workflow directly.

On macOS, the Python CLI preserves the original app workflow: stop Codex App, switch the workspace link, and start Codex App again. On Linux and Windows, app control is skipped and the CLI only switches the workspace link.

## Features

- Manage workspace directories such as `~/.codex-workspaces/workspaces/work`.
- Manage account snapshots under `~/.codex-workspaces/accounts/`.
- Switch the active `~/.codex` symlink or directory link.
- Initialize workspace directories with metadata.
- Temporarily switch the current workspace account with `accounts use`, then restore the workspace default account.
- Keep macOS Codex App stop/start/restart support.
- Show local token usage stats from Codex `state_*.sqlite` in read-only mode.
- Block unsafe operations from a detected Codex built-in terminal when they cannot be delegated safely.
- Support English and Chinese output through `CODEX_WORKSPACES_LANG`.
- Package as a Python project with tests, CI, and PyPI publishing workflow.

## Requirements

- Python 3.9 or newer for the Python CLI.
- macOS is required only for Codex App control commands: `start`, `stop`, and `restart`.
- Linux and macOS use directory symlinks.
- Windows uses directory symlinks when available and falls back to directory junctions.

## Install

Install the Python CLI from PyPI:

```bash
python3 -m pip install codex-workspaces
```

For isolated CLI installs, `pipx` is recommended:

```bash
pipx install codex-workspaces
```

Install from a local checkout for development:

```bash
python3 -m pip install -e ".[dev]"
```

The legacy macOS shell installer is still available from the `macos/` directory:

```bash
tmp="$(mktemp -t codex-workspaces.XXXXXX)" && curl -fsSL https://raw.githubusercontent.com/blockchain-project-lives/codex-workspaces/main/macos/codex-workspaces -o "$tmp" && bash "$tmp" install && rm -f "$tmp"
```

## Workspace Layout

Default layout:

```text
~/.codex           -> active workspace link
~/.codex-workspaces/
  config.json
  state.json
  lock
  workspaces/
    work/
      auth.json
      .codex-workspace.json
    personal/
      auth.json
      .codex-workspace.json
  accounts/
    acct_work/
      auth.json
      meta.json
```

Customize paths with `CODEX_WORKSPACES_LINK` and `CODEX_WORKSPACES_ROOT`.

## Usage

Initialize workspaces:

```bash
codex-workspaces init personal
codex-workspaces init work
```

Migration from older `~/.codex-<name>` directories is intentionally deferred to a later phase. This release initializes new managed workspaces only.

Set up account snapshots after Codex has created an `auth.json` in the active workspace:

```bash
codex-workspaces use work --no-stop --no-start
codex-workspaces accounts save work
codex-workspaces accounts set-default work acct_work --activate
codex-workspaces accounts list
```

Switch workspaces:

```bash
codex-workspaces work
codex-workspaces use personal
codex-workspaces switch work
```

On macOS, switching stops and restarts Codex App by default. Skip those steps when needed:

```bash
codex-workspaces work --no-stop --no-start
```

Inspect workspaces:

```bash
codex-workspaces list
codex-workspaces current
codex-workspaces doctor
codex-workspaces stats
codex-workspaces stats work --days 14
```

Switch accounts within the current workspace:

```bash
codex-workspaces accounts use acct_personal
codex-workspaces accounts restore-default
```

`accounts use` only changes the current workspace `active_account_id`; it does not change `default_account_id`. Entering a workspace with `codex-workspaces use <workspace>` restores that workspace's default account when one is configured.

Manage workspace metadata and lifecycle:

```bash
codex-workspaces note work "main paid workspace"
codex-workspaces rename work main
codex-workspaces delete old-workspace --force
```

Control Codex App on macOS:

```bash
codex-workspaces stop
codex-workspaces start
codex-workspaces restart
```

`stats` only reads local SQLite files such as `state_*.sqlite` or `sqlite/state_*.sqlite`. It does not call quota or refresh private APIs.

## Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| `CODEX_APP_NAME` | `Codex` | macOS app name to control. |
| `CODEX_QUIT_TIMEOUT` | `20` | Seconds to wait for app exit. |
| `CODEX_WORKSPACES_LINK` | `$HOME/.codex` | Active workspace link path. |
| `CODEX_WORKSPACES_ROOT` | `$HOME/.codex-workspaces` | Managed root for workspaces, accounts, backups, and lock file. |
| `CODEX_WORKSPACES_LANG` | auto | Force output language with `en` or `zh`. |

Only the `CODEX_WORKSPACES_*` variables are used for workspace-specific configuration.

## Development

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
```

Design, test, and release notes live in [`docs/`](docs/).

## Publishing

CI runs tests on Linux, macOS, and Windows across Python 3.9, 3.11, and 3.13. The `Publish to TestPyPI` workflow runs for `v*` tags, and the `Publish to PyPI` workflow publishes from `release/v*` branches or manual runs.

Configure TestPyPI and PyPI Trusted Publishing for this repository before using the release workflows. See [`docs/RELEASE.zh-CN.md`](docs/RELEASE.zh-CN.md).
