#!/usr/bin/env bash
# Runs on every container start (postStartCommand), including restarts of an
# existing container. Output: ~/var/log/devcontainer-poststart.log
# Everything here must be safe to run repeatedly.
set -Eeuo pipefail

# Site environment (its .profile needs nounset off)
set +u
source /omd/sites/cmk/.profile
set -u

WORKSPACE_DIR="${WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"

# Stale PID files from the previous container run would keep services from starting
find "$OMD_ROOT/tmp" -type f -name "*.pid" -delete || true

# Register the workspace's MKP manifest (file "package" in the repo root) so
# `mkp package` / build.sh can use it.
PKG_DIR="$OMD_ROOT/var/check_mk/packages"
pkg_file="$WORKSPACE_DIR/package"
if [[ -f "$pkg_file" ]]; then
  if pkg_name=$(python3 -c "import ast,sys; print(ast.literal_eval(open(sys.argv[1]).read())['name'])" "$pkg_file"); then
    if [[ ! -e "$PKG_DIR/$pkg_name" ]]; then
      ln -s "$pkg_file" "$PKG_DIR/$pkg_name"
      echo "Registered MKP package manifest: $pkg_name"
    fi
  else
    echo "WARNING: could not read package name from $pkg_file"
  fi
fi

# Checkmk plugin dev skill, as a Claude Code plugin from its self-hosted
# marketplace on GitHub. .claude/settings.json in the repo declares the same,
# but that only takes effect in an interactive session; these commands make
# sure it is installed and current on every start. Failures (e.g. no network)
# must not block the site start below.
SKILL_MARKETPLACE_REPO="chexma/claude_code_checkmk_plugin_skill"
SKILL_MARKETPLACE="chexma-checkmk"
SKILL_PLUGIN="checkmk-plugin-dev@${SKILL_MARKETPLACE}"
if command -v claude >/dev/null 2>&1; then
  # Capture output first: `cmd | grep -q` can SIGPIPE cmd, which pipefail
  # would turn into a false "not found".
  marketplaces=$(claude plugin marketplace list 2>/dev/null || true)
  plugins=$(claude plugin list 2>/dev/null || true)
  if ! grep -q "$SKILL_MARKETPLACE" <<<"$marketplaces"; then
    claude plugin marketplace add "$SKILL_MARKETPLACE_REPO" || echo "WARNING: adding marketplace $SKILL_MARKETPLACE failed"
  else
    claude plugin marketplace update "$SKILL_MARKETPLACE" || echo "WARNING: updating marketplace $SKILL_MARKETPLACE failed"
  fi
  if ! grep -q "$SKILL_PLUGIN" <<<"$plugins"; then
    claude plugin install "$SKILL_PLUGIN" || echo "WARNING: installing $SKILL_PLUGIN failed"
  else
    claude plugin update "$SKILL_PLUGIN" || echo "WARNING: updating $SKILL_PLUGIN failed"
  fi
else
  echo "WARNING: claude not found, skipping skill plugin setup"
fi

# Start the site (restart also covers a half-started site after a container restart)
timeout 120s omd restart || omd restart

cmk-update-license-usage || true

omd status || true
