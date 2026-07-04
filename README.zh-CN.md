# codex-accounts

[English](README.MD) | 简体中文 | [更新日志](CHANGELOG.md)

`codex-accounts` 用来切换多个 Codex 账号目录。默认把每个账号放在 `~/.codex-<账号名>`，并让当前生效的 `~/.codex` 指向选中的账号。

项目现在有两个入口：

- 跨平台 Python 3 CLI，支持 Linux、macOS 和 Windows。
- 原来的 macOS Bash 脚本，仍保留在 [`codex-accounts`](codex-accounts)，兼容已经使用 shell 安装方式的用户。

在 macOS 上，Python CLI 保留原来的 App 流程：关闭 Codex App、切换账号链接、再启动 Codex App。在 Linux 和 Windows 上，CLI 会跳过 App 启停，只切换账号链接。

## 功能

- 管理 `~/.codex-work`、`~/.codex-personal` 这类账号目录。
- 切换当前 `~/.codex` 软链接或目录链接。
- 创建账号目录，并支持把已有真实 `~/.codex` 目录迁移成账号。
- 保留 macOS 上 Codex App 的 `stop`、`start`、`restart`。
- 在检测到 Codex 内置 Terminal 且无法安全转交时，阻止危险操作。
- 支持中英文输出，可通过 `CODEX_ACCOUNTS_LANG` 指定。
- 提供 Python 包、测试、GitHub CI 和 PyPI 发布工作流。

## 要求

- Python 3.9 或更新版本。
- 只有 `start`、`stop`、`restart` 这类 Codex App 控制命令要求 macOS。
- Linux 和 macOS 使用目录软链接。
- Windows 优先使用目录软链接，不可用时回退到目录 junction。

## 安装

从 PyPI 安装 Python CLI：

```bash
python3 -m pip install codex-accounts
```

推荐用 `pipx` 做隔离安装：

```bash
pipx install codex-accounts
```

本地开发安装：

```bash
python3 -m pip install -e ".[dev]"
```

旧版 macOS shell 安装方式仍可使用：

```bash
tmp="$(mktemp -t codex-accounts.XXXXXX)" && curl -fsSL https://raw.githubusercontent.com/blockchain-project-lives/codex-accounts/main/codex-accounts -o "$tmp" && bash "$tmp" install && rm -f "$tmp"
```

## 账号目录

默认布局：

```text
~/.codex           -> 当前账号链接
~/.codex-work      名为 work 的账号目录
~/.codex-personal  名为 personal 的账号目录
```

可通过 `CODEX_ACCOUNTS_LINK` 和 `CODEX_ACCOUNTS_PREFIX` 自定义路径。

## 使用

创建账号：

```bash
codex-accounts create personal
codex-accounts create work
```

如果已经有一个真实存在的 `~/.codex` 目录，先迁移：

```bash
codex-accounts create personal --migrate-current
```

切换账号：

```bash
codex-accounts work
codex-accounts use personal
codex-accounts switch work
```

macOS 上默认会在切换前后关闭和启动 Codex App。需要时可以跳过：

```bash
codex-accounts work --no-stop --no-start
```

查看账号：

```bash
codex-accounts list
codex-accounts current
```

macOS 上控制 Codex App：

```bash
codex-accounts stop
codex-accounts start
codex-accounts restart
```

## 环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `CODEX_APP_NAME` | `Codex` | macOS App 名称。 |
| `CODEX_QUIT_TIMEOUT` | `20` | 等待 App 退出的秒数。 |
| `CODEX_ACCOUNTS_LINK` | `$HOME/.codex` | 当前账号链接路径。 |
| `CODEX_ACCOUNTS_PREFIX` | `$HOME/.codex-` | 账号目录前缀。 |
| `CODEX_ACCOUNTS_LANG` | 自动 | 强制输出语言，可设为 `en` 或 `zh`。 |

兼容旧变量：`CODEX_ACCOUNT_LINK`、`CODEX_ACCOUNT_PREFIX`、`CODEX_ACCOUNT_LANG`。

## 开发

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
python3 -m build
python3 -m twine check dist/*
```

设计、测试和发布说明见 [`docs/`](docs/)。

## 发布

CI 会在 Linux、macOS、Windows 上测试 Python 3.9、3.11、3.13。`Publish to PyPI` 工作流会在 GitHub Release 发布或手动触发时构建并发布到 PyPI。

发布前需要在 TestPyPI 和 PyPI 分别配置 Trusted Publishing。详见 [`docs/RELEASE.zh-CN.md`](docs/RELEASE.zh-CN.md)。
