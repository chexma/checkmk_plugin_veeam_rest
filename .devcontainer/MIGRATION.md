# Migrating an existing plugin to this template

Instructions for Claude Code. They cover plugin folders from older
devcontainer setups (e.g. derived from `Yogibaer75/checkmk_template`): with
or without a git repo, Claude Code installed via npm, Claude config inside
the workspace. Claude normally runs **inside the plugin's old devcontainer**;
step 1.0 covers a stopped or deleted container (Claude on the host).

The migration has two phases with a container rebuild in between:

- **Phase 1** (old container or host): back up container-only state, put the
  folder on the template's git history, take over template files, merge the
  rest, commit. Nothing inside `.claude/` is deleted in this phase: in old
  setups the running Claude session keeps its config there.
- The user rebuilds the container (VS Code, or the Dev Containers CLI, see phase 2).
- **Phase 2** (new container): restore memory and test hosts, verify, clean up.

Start prompts for the user:

```text
Phase 1: Add https://github.com/chexma/checkmk-plugin-template.git as git
remote "template" (run `git init -b main` first if this is no git repo),
fetch it and follow `git show template/main:.devcontainer/MIGRATION.md`, phase 1.

Phase 2: Follow .devcontainer/MIGRATION.md, phase 2.
```

General rules for both phases:

- Before anything that deletes, overwrites or commits, show what will happen
  and wait for the user's OK. Never push.
- Run each overwriting or deleting step as its own command, right after
  showing it; don't chain them with `&&`. Claude Code's permission check
  refuses large combined destructive commands even after an OK in chat.
- Never use `mkp release` or `mkp disable` (they delete the bind-mounted
  sources).
- Never print or copy `.claude/.credentials.json` or other secrets.
- `<name>` below is the plugin/package name (`name` in the manifest `package`).
- Work from the workspace root (`$WORKSPACE`, e.g. `/workspaces/sep_sesam`;
  on the host: the plugin folder).
- If git reports "detected dubious ownership", run
  `git config --global --add safe.directory "$WORKSPACE"` (the bind-mounted
  workspace belongs to the host user; new containers set this up themselves).

---

## Phase 1: in the old container (or on the host)

### 1.0 Where am I?

If `cmk` and `$OMD_ROOT` exist, Claude runs inside the old container:
continue with 1.1. Otherwise Claude runs on the host; look for the old
container:

```bash
docker ps -a --filter "label=devcontainer.local_folder=$PWD" --format '{{.Names}} {{.Status}}'
```

- **stopped**: `docker start <name>`; run the site exports of 1.2 with
  `docker exec -u cmk <name> bash -lc '...'` (REST API via `curl` inside).
- **none** (deleted): continue on the host. 1.2.3 (manifest from the site)
  and 1.2.4 (hosts, rules) are impossible; note in `site.md` that the site
  state could not be exported. Use `$PWD` as workspace. On macOS use BSD
  tool syntax (`sed -i ''`).

### 1.1 Inventory, then stop

Collect and show the user:

- git: repo or not, **branch name** (`master`, see 1.3), remotes,
  `git status --short` (uncommitted work?)
- plugin code: `plugins/*/`, and whether a duplicate `local/lib/python3/cmk_addons/plugins/`
  exists in the workspace (`diff -rq` against `plugins/`, ignoring `__pycache__`)
- `plugins_legacy/`: real legacy code (`checks/`, `web/`, …) vs. build
  artifacts (`enabled_packages/`)
- `lib/`, `agents/`, `bin/`, `nagios_plugins/`, `tests/`, `test/` (often empty)
- manifest `package` (name, version, files) and `*.mkp` files
- docs and notes: `docs/`, `plans/`, `idea.md`, `ToDO`, `Installation.md`, `temp/`
- files the old `.gitignore` hides that the template's would not, and large
  files: `git ls-files --others --ignored --exclude-standard` (still with the
  old `.gitignore`) and `find . -path ./.git -prune -o -type f -size +5M -print`
  (e.g. a simulator tarball); they would be committed in 1.7
- `.devcontainer/devcontainer.json`: Checkmk edition (image `checkmk/check-mk-<edition>`
  in the Dockerfile) and `VARIANT`, fixed ports, extra mounts
- `echo $CLAUDE_CONFIG_DIR` and whether it points into the workspace
- `CLAUDE.md`: tracked by git, and pushed? Its plugin content moves to the
  untracked `CLAUDE.local.md` (1.5); tell the user that anything already
  pushed stays readable in the repo history
- names of **other** plugins in this plugin's files: old setups were copied
  between plugins, e.g. a `build.sh` hard-coded to another package or MKP
  details of another plugin in `CLAUDE.md`. List every hit
  (`grep -rIl` for the other plugin names you find, outside `.claude/`); such
  content is dropped in the merge.
- tests that depend on the old layout: paths into a workspace copy
  (`local/lib/python3/...`), `sys.path` tweaks, stubs replacing `cmk` modules
- symlinks in the site's `~/local` (`find ~/local -type l -printf "%p -> %l\n"`):
  old setups linked `~/local/tmp` and `~/local/lib/nagios/plugins` to the
  workspace. The new container uses bind mounts instead; anything else
  pointing to a directory outside `~/local` breaks config generation on
  Checkmk 2.5. References to `~/local/tmp` (docs, tests, scripts) must point
  to the workspace's `temp/` instead.

Then ask the user to confirm that a **copy of the whole plugin folder exists
on the host** (e.g. `cp -a sep_sesam sep_sesam.bak`). Do not continue without it.
That copy also matters later: `CLAUDE.local.md` is never in git.

### 1.2 Back up container-only state

Into `temp/claude-migration/` (`temp/` is not tracked; it survives the
rebuild because it is in the workspace):

1. **Claude memory**: the project's memory dir is
   `projects/<slug>/memory/` in the Claude config dir. `<slug>` is the
   workspace path with every non-alphanumeric character replaced by `-`
   (`/workspaces/sep_sesam` → `-workspaces-sep-sesam`). Look in
   `$CLAUDE_CONFIG_DIR` (default `~/.claude`) **and** in the workspace's
   `.claude/` (old setups pointed the config dir there; on the host that is
   the only place). Copy it to `temp/claude-migration/memory/`. If there is
   none, note that in `temp/claude-migration/site.md` and continue.
2. **Old Claude settings**: copy the old config dir's `settings.json` to
   `temp/claude-migration/old-user-settings.json` (step 1.4 overwrites
   `.claude/settings.json` in the workspace, which may be that file), and
   `.claude/settings.local.json` if present to
   `temp/claude-migration/old-settings.local.json`.
3. **Manifest**: if `package` is not in the workspace root, copy it from
   `~/var/check_mk/packages/<name>`. If neither has it, extract it from the
   newest `*.mkp` (a tar.gz whose `info` member is the manifest):
   `tar xzf <name>-<version>.mkp -O info > package`. Review `author` (MKPs
   built in the GUI say `cmkadmin`), `download_url` (may point to another
   repo) and `files`.
4. **Test setup of the site**: the site itself is rebuilt from scratch.
   Write `temp/claude-migration/site.md` with the hosts (`cmk --list-hosts`)
   and, via the REST API (`http://localhost:5000/cmk/check_mk/api/1.0`, user
   `cmkadmin`, password `cmkadmin`), export the rules of the plugin's rulesets
   to `temp/claude-migration/rules-*.json`: `datasource_programs`, check
   parameter rulesets of the plugin, and the special agent's
   `special_agents:<agent>`, where `<agent>` is the `name` of the
   `SpecialAgent` in `server_side_calls/`, which can differ from the plugin
   name. Stored passwords are not exported in clear text; note which ones
   the user has to re-enter.
   Note which files hold canned agent output (e.g. `temp/agent_output.txt`).

### 1.3 Put the folder on the template history

```bash
git remote add template https://github.com/chexma/checkmk-plugin-template.git
git fetch template
```

If the fetch fails (private repo, no credentials in the container): ask the
user to clone the template on the host into the workspace's `temp/`, then
`git remote add template "$WORKSPACE/temp/checkmk-plugin-template"`, and at
the end of phase 1
`git remote set-url template https://github.com/chexma/checkmk-plugin-template.git`.

- **No git repo yet:**
  ```bash
  git init -b main          # if not done already
  git reset template/main   # HEAD and index = template, working files untouched
  ```
  `git status` now shows the plugin's files as changes against the template.
- **Existing repo:** working tree must be clean (ask the user to commit or stash
  first). A repo on `master`: offer `git branch -m master main` (CI runs on
  both, but new repos use `main`); the user then renames the default branch
  on GitHub (Settings → Branches, or
  `gh api -X POST repos/<owner>/<repo>/branches/master/rename -f new_name=main`)
  and runs `git fetch --prune origin && git branch -u origin/main main`.
  Then
  ```bash
  git merge -s ours --no-commit --allow-unrelated-histories template/main
  ```
  This records the template history without changing any file; the next
  steps bring in the template files, and the commit in 1.7 concludes the merge.

Either way, `git pull template main` will later bring only new template changes.

### 1.4 Take over the template's files

```bash
git checkout template/main -- .devcontainer .claude/settings.json .claude/hooks \
    .github .gitattributes .flake8 .gitignore
```

- Template placeholders (`tests/.gitkeep`, `agents/.gitkeep`, …):
  - no-repo case: they show up as deleted (`git ls-files --deleted`);
    restore them with `git checkout -- <paths>` unless the user wants a file gone
  - existing-repo case: the merge took none of them; add the missing ones:
    ```bash
    for f in $(git ls-tree -r --name-only template/main | grep '\.gitkeep$'); do
      git cat-file -e "HEAD:$f" 2>/dev/null || git checkout template/main -- "$f"
    done
    ```
- Remove old devcontainer files the template does not have, e.g.
  `.devcontainer/setpwd.sh`, `template-update.sh`, `template-sync*.conf`,
  `requirements.txt`, backup copies (`*.org`, `*.orig`, `*.bak`)
  (`git rm` if tracked, else `rm`).
- In `.devcontainer/devcontainer.json` set `EDITION` and `VARIANT` to the
  values the old setup used (old Dockerfiles often hard-code
  `checkmk/check-mk-cloud`, i.e. `EDITION=cloud`). Ask the user whether to
  move to the template's `VARIANT` now or later (later = fewer changes at once).
  Moving to 2.5 also changes `EDITION` (renamed editions: `cloud` →
  `ultimate`, `enterprise` → `pro`, `raw` → `community`).
- Old resource settings (`--cpus`, `--memory`, `NODE_OPTIONS`) are dropped
  with the old `devcontainer.json`; see the README notes if Pylance runs out
  of memory.
- `.gitignore` is the template's. If the old one tracked less (e.g. only the
  plugin code), keep the template's and show the user in 1.6 what becomes
  tracked. For each large or formerly hidden file from 1.1 ask: move to
  `temp/`, add to `.gitignore`, or delete.

### 1.5 Merge the files that belong to both

- **`CLAUDE.md` / `CLAUDE.local.md`**: plugin-specific instructions are kept
  private in `CLAUDE.local.md` (ignored by git, loaded by Claude Code next to
  `CLAUDE.md`); the tracked `CLAUDE.md` stays exactly the template's.
  1. Write `CLAUDE.local.md` from the old `CLAUDE.md` (and an old
     `CLAUDE.local.md`, if any): purpose, external system, status,
     architecture, conventions, plugin-specific commands such as agent test
     calls (with paths adjusted to `plugins/<name>/...`), test data and a
     `test-host.sh` example. Replace line-number references ("around line
     402") with function names; they go stale. Drop what the template's
     `CLAUDE.md` already covers (environment, mounts, MKP build steps,
     Python tools, the old container) and content of other plugins (1.1).
  2. Only then: `git checkout template/main -- CLAUDE.md`.
  3. Check `git check-ignore CLAUDE.local.md` prints the file name.
- **`pyproject.toml`**: start from the template's. Keep plugin sections that
  have an effect (e.g. `[tool.isort]` `known_first_party`, extra pytest
  options). Drop `[tool.flake8]` (flake8 does not read `pyproject.toml`; move
  needed rules such as `per-file-ignores = __init__.py:F401` into `.flake8`),
  pylint sections (not part of the toolchain) and `[project]` (no installable
  package).
- **`README.md`**: keep the plugin's. Check for
  - download hints pointing to MKPs in the repo: they are untracked from now
    on (1.6); ask the user to link the Releases page
    (`https://github.com/<owner>/<repo>/releases/latest`); the first release
    comes from a `v<version>` tag after phase 2
  - outdated paths: `grep -n 'agents/special\|cmk\.plugins\.' README.md`
    (pre-2.3 special agent location is now
    `local/lib/python3/cmk_addons/plugins/<name>/libexec/agent_<x>`)
- **`Changelog.md`**: keep the plugin's. If there is none, take the
  template's stub and add an entry for the current `version` from `package`
  (date of the last commit), so the first release has one.
- **`package`**: keep; check `name` matches `plugins/<name>/` and `files`
  lists exist.
- **Tests**: point paths into a workspace copy (`local/lib/python3/cmk_addons/plugins/<name>/...`)
  to `plugins/<name>/...` before that copy is removed in 1.6. Leave stubs and
  assertions alone; phase 2 shows whether the tests pass.

### 1.6 Clean up

- Duplicate `local/lib/python3/cmk_addons/plugins/…` in the workspace: delete
  only if identical to `plugins/` (1.1); otherwise ask the user which is current.
- `plugins_legacy/`: keep real legacy code; `enabled_packages/` is ignored by
  the template's `.gitignore` and needs no action. An empty
  `plugins_legacy/agents/` is the mount point of the `agents/` bind mount:
  leave it.
- Built `*.mkp`: ignored now; if they were tracked, `git rm --cached` them
  (releases come from CI).
- Empty directories, e.g. `test/` or `lib/gui/plugins/*` from old templates:
  remove. `.keep` files in tracked plugin dirs are harmless (not in the
  manifest); remove them only where the dir has content.
- Notes and docs (`docs/`, `plans/`, `idea.md`, `ToDO`, `Installation.md`, …):
  list them and let the user decide per item: track, ignore (add to
  `.gitignore`) or delete.
- `.claude/` (old config dir in the workspace): **leave as is**; the
  template's `.gitignore` already hides everything except `settings.json`
  and `hooks/`.

### 1.7 Review and commit

```bash
git add -A
git status --short
git diff --cached --stat | tail -1
```

Show a short summary of what is tracked, changed, removed. Stop and ask on:

- secrets: `git diff --cached --name-only | grep -iE 'credential|\.claude\.json'`
  must be empty
- large files: anything over 5 MB in the index
  (`git diff --cached --name-only | xargs -I{} find {} -size +5M 2>/dev/null`)

After the user's OK:

```bash
git commit -m "Migrate to checkmk-plugin-template"
```

Tell the user: end this session, then rebuild the container ("Dev
Containers: Rebuild Container" in VS Code, or see phase 2 for the CLI) and
start phase 2 in the new container. The fixed host port of the old setup is
gone: the GUI is on the port VS Code forwards for 5000 (Ports view).

---

## Phase 2: in the new container

On the first `claude` start: log in if asked (shared volume
`checkmk-claude-config`) and **accept the trust dialog** for the workspace;
until then the project's permissions and the format hook are ignored.

Without VS Code (e.g. Claude on the host), the Dev Containers CLI builds and
starts the container exactly like VS Code (lifecycle scripts, mounts, label
for "Reopen in Container"); run commands with `docker exec`:

```bash
npx -y @devcontainers/cli@latest up --workspace-folder .
docker exec -u cmk -w /workspaces/<folder> <container> bash -lc '<command>'
```

1. **`CLAUDE.local.md`** must exist in the repo root and be ignored by git
   (`git check-ignore CLAUDE.local.md`); remind the user that it is not
   backed up by git.
2. **Memory**: skip if `temp/claude-migration/memory/` does not exist. The
   slug is the same if the folder name did not change. Copy
   `temp/claude-migration/memory/*` into `$CLAUDE_CONFIG_DIR/projects/<slug>/memory/`
   without overwriting existing files; if both have a `MEMORY.md`, merge the
   index lines.
3. **Test setup**: recreate hosts with canned agent output via
   `.devcontainer/test-host.sh <host> <file>`; recreate special agent and
   parameter rules from `temp/claude-migration/rules-*.json` via the REST API
   (ask the user for passwords). Activate changes. A password field in
   `value_raw` (Checkmk 2.4 form specs) looks like
   `("cmk_postprocessed", "explicit_password", ("<any-id>", "<secret>"))`;
   the ruleset is `special_agents:<agent>` (1.2.4). `cmk -D <host>` shows the
   resulting agent call.
4. **Verify**:
   - `mkp list` shows the package (registered by `startup.sh` from `package`)
   - `cmk -U` succeeds (core config generation; on 2.5 it fails on symlinks
     in `~/local` that point to directories outside it)
   - Before changing code: save `cmk -v --detect-plugins=<plugins> <host>`
     per test host to `temp/claude-migration/before-<host>.txt`, to diff
     after formatting and fixes (ignore PEND lines and the `[agent]` timing line).
   - `.devcontainer/ci.sh`: if black/isort reformat the old code, run
     `isort plugins tests && black plugins tests` and commit that separately
     ("Format with pinned black/isort").
   - Report remaining findings to the user with their cause: flake8,
     failing tests, `cmk-validate-plugins` errors (e.g. a `check_ruleset_name`
     without a matching rule spec). They were there before the migration:
     don't change assertions or code to make them pass, the user decides.
     Until they are fixed, CI on the first push is red.
   - `cmk -vI` / `cmk -v --detect-plugins=<plugin> <host>` on a test host
   - optional: `.devcontainer/build.sh` (builds the current version from `package`)
5. **Clean up** after the user's OK:
   - old MKPs in `plugins_legacy/enabled_packages/` (the old site's state; the
     new site lists them as inactive versions in `mkp list`, and `build.sh`
     recreates the current one)
   - `temp/claude-migration/`
   - `.claude/`: keep `settings.json`, `hooks/` and `settings.local.json`
     (show its entries; the user decides what stays). Everything else there
     (old login, history, sessions, cloned skills, backups) the user deletes:
     Claude Code's permission check refuses it. Hand them the command to run
     with `!` or in a terminal:
     ```bash
     find .claude -mindepth 1 -maxdepth 1 ! -name settings.json ! -name settings.local.json ! -name hooks -exec rm -rf {} +
     ```
6. Commit. A repo without `origin`: the user creates the GitHub repo, then
   `git remote add origin <url>`; push only when asked. CI runs on the first
   push; a first release comes from pushing a tag `v<version>`.
