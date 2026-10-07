#!/usr/bin/env bash
# Build the MKP from the manifest file "package" in the repo root and copy it
# into the workspace. Run as the site user inside the devcontainer (or in CI).
#
# Only build on purpose: never use `mkp release` or `mkp disable` here, they
# delete the bind-mounted source files.
set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-$(cd "$(dirname "$0")/.." && pwd)}"
MANIFEST="${WORKSPACE}/package"
OMD_ROOT="${OMD_ROOT:-/omd/sites/cmk}"
CMK_PACKAGES_PATH="${OMD_ROOT}/var/check_mk/packages"

if [[ ! -f "$MANIFEST" ]]; then
    echo "ERROR: no MKP manifest at ${MANIFEST} (create one with 'mkp template <name>', see README)"
    exit 1
fi

read -r PKG_NAME VERSION < <(python3 -c '
import ast, sys
m = ast.literal_eval(open(sys.argv[1]).read())
print(m["name"], m["version"])
' "$MANIFEST")
echo "Building ${PKG_NAME} ${VERSION}..."

# The manifest lives in the repo; mkp expects it under var/check_mk/packages
ln -sfn "$MANIFEST" "${CMK_PACKAGES_PATH}/${PKG_NAME}"

MKP_FILE="${OMD_ROOT}/var/check_mk/packages_local/${PKG_NAME}-${VERSION}.mkp"
rm -f "$MKP_FILE"
mkp package "${CMK_PACKAGES_PATH}/${PKG_NAME}"

if [[ ! -f "$MKP_FILE" ]]; then
    echo "ERROR: MKP file not found at ${MKP_FILE}"
    exit 1
fi
cp "$MKP_FILE" "${WORKSPACE}/"
echo "SUCCESS: ${PKG_NAME}-${VERSION}.mkp"

# GitHub Actions output (if running in CI)
if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "pkgfile=${PKG_NAME}-${VERSION}.mkp"
        echo "pkgname=${PKG_NAME}"
        echo "pkgversion=${VERSION}"
    } >> "$GITHUB_OUTPUT"
fi
