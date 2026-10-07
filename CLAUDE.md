# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project

This file is generic and tracked by git (it comes from the template). All
plugin-specific context (purpose, external system, architecture,
conventions, notes) lives in `CLAUDE.local.md` in the repo root, which is
**not** tracked. Put new plugin knowledge there, never into this file. If
`CLAUDE.local.md` is missing, tell the user. The package name is `name` in
`package`; `<name>` below stands for it.

Use the `checkmk-plugin-dev` skill (installed as Claude Code plugin
`checkmk-plugin-dev@chexma-checkmk`) for CheckMK API references and templates.

## Environment

Devcontainer based on the official `checkmk/check-mk-<edition>` image with a
running site `cmk` (GUI: forwarded port 5000, path `/cmk/`, `cmkadmin`/`cmkadmin`).
Edition and version are set in `.devcontainer/devcontainer.json` (build args).
The shell runs as site user `cmk`, so `cmk`, `mkp`, `omd` work directly.

Workspace directories are bind-mounted into the site:

| Workspace | Site path |
|---|---|
| `plugins/` | `~/local/lib/python3/cmk_addons/plugins/` |
| `lib/` | `~/local/lib/python3/cmk/` |
| `plugins_legacy/` | `~/local/share/check_mk/` |
| `agents/` | `~/local/share/check_mk/agents/` |
| `bin/` | `~/local/bin/` |
| `nagios_plugins/` | `~/local/lib/nagios/plugins/` |
| `temp/` | not in the site; scratch space at `$WORKSPACE/temp`, not tracked |

Never create symlinks in `~/local` that point to directories outside it:
since Checkmk 2.5 every config generation (`cmk -U`/`-R`, activation)
snapshots `~/local` and fails on them (`IsADirectoryError`).

`sudo` is not available to Claude Code sessions, and the container cannot
rebuild itself (no Docker socket); rebuilds are done from VS Code on the host.

## Commands

```bash
black plugins/ tests/                 # format (line length 100, see pyproject.toml)
isort plugins/ tests/
flake8 plugins/ tests/
pytest                                # tests/ (pytest ships with the site)
.devcontainer/ci.sh                   # everything CI runs (lint, tests, validate)

cmk-validate-plugins                  # all plugins load?
.devcontainer/test-host.sh <host> <agent-output-file>   # host with canned agent output
cmk -vI --detect-plugins=<plugin> <host>   # discovery
cmk -v --detect-plugins=<plugin> <host>    # check
cmk -R                                # reload config after check plugin changes
omd restart apache                    # after ruleset/graphing changes
```

## MKP packaging

Build MKPs **only on explicit request**, not after every change.

**Never use `mkp release` or `mkp disable`** — they delete the bind-mounted
source files in the workspace (also denied in `.claude/settings.json`).

A PostToolUse hook (`.claude/hooks/format-python.sh`) runs isort and black on
every Python file you edit; don't reformat by hand afterwards.

The manifest is the file `package` in the repo root (tracked in git).
`.devcontainer/startup.sh` links it into `~/var/check_mk/packages/<name>`.

First time (no `package` file yet):

```bash
mkp template <name>    # writes ~/tmp/check_mk/<name>.manifest.temp
# Trim it to this plugin's files only (it lists ALL unpackaged files of the
# site), set title/author/description/version/version.min_required, then:
cp ~/tmp/check_mk/<name>.manifest.temp "$WORKSPACE/package"
```

Each build:

```bash
# 1. bump 'version' in ./package, add new files to its 'files' dict
# 2. build and copy the .mkp into the workspace
.devcontainer/build.sh
# 3. update Changelog.md
```
