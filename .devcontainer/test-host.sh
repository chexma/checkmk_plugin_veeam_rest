#!/usr/bin/env bash
# Create (or update) a host in the dev site whose agent output comes from a
# file in the workspace, for discovery/check runs against canned data.
#
#   .devcontainer/test-host.sh <host> <agent-output>   # create or update
#   .devcontainer/test-host.sh --remove <host>         # delete again
#
# <agent-output> is either a plain file with agent output (it is cat'ed) or an
# executable script (starting with #!) that prints it. Afterwards:
#   cmk -vI --detect-plugins=<plugin> <host>    # discovery
#   cmk -v --detect-plugins=<plugin> <host>     # check
#
# Uses the REST API: hand-written hosts in conf.d/*.mk don't get the
# datasource program applied reliably.
set -Eeuo pipefail

API="http://localhost:5000/cmk/check_mk/api/1.0"
AUTH="Authorization: Bearer cmkadmin cmkadmin"

usage() {
    sed -n '5,6p' "$0" | sed 's/^#   /usage: /'
    exit 2
}

api() {
    # api METHOD PATH [JSON] -> body on stdout, fails on HTTP >= 400
    local method=$1 path=$2 data=${3:-}
    local args=(-sS -X "$method" -H "$AUTH" -H "Accept: application/json" -w '\n%{http_code}')
    [[ -n "$data" ]] && args+=(-H "Content-Type: application/json" -d "$data")
    [[ "$method" == DELETE || "$path" == */activate-changes/invoke ]] && args+=(-H "If-Match: *")
    local out code
    out=$(curl "${args[@]}" "$API$path")
    code=${out##*$'\n'}
    out=${out%$'\n'*}
    if ((code >= 400)); then
        echo "ERROR: $method $path -> HTTP $code: $out" >&2
        ((code == 401)) && echo "(post-create.sh sets the login cmkadmin/cmkadmin this script uses)" >&2
        return 1
    fi
    printf '%s' "$out"
}

# Rules this script created for a host carry this marker in their description.
rule_marker() { echo "test-host.sh:$1"; }

remove_rules() {
    local host=$1 ids
    ids=$(api GET "/domain-types/rule/collections/all?ruleset_name=datasource_programs" |
        jq -r --arg m "$(rule_marker "$host")" '.value[] | select(.extensions.properties.description == $m) | .id')
    for id in $ids; do
        api DELETE "/objects/rule/$id" >/dev/null
    done
}

host_exists() {
    curl -sS -o /dev/null -w '%{http_code}' -H "$AUTH" "$API/objects/host_config/$1" | grep -q '^200$'
}

activate() {
    # The activation runs in the background: wait for it and check the result,
    # otherwise a failing config generation goes unnoticed.
    local run id errors
    run=$(api POST /domain-types/activation_run/actions/activate-changes/invoke \
        '{"redirect": false, "sites": [], "force_foreign_changes": true}') || {
        echo "WARNING: activating changes failed (cmk -I/-v still work, the GUI lags behind)"
        return 0
    }
    id=$(jq -r .id <<<"$run")
    # 204 = finished; anything else means it is still running
    for _ in $(seq 1 60); do
        [[ "$(curl -sS -o /dev/null -w '%{http_code}' -H "$AUTH" \
            "$API/objects/activation_run/$id/actions/wait-for-completion/invoke")" == 204 ]] && break
        sleep 2
    done
    errors=$(api GET "/objects/activation_run/$id" |
        jq -r '.extensions.status_per_site[]? | select(.state != "success") | "\(.site): \(.status_details)"')
    if [[ -n "$errors" ]]; then
        echo "WARNING: activating changes failed (cmk -I/-v still work, run 'cmk -U' for details):" >&2
        echo "$errors" >&2
    fi
}

if [[ "${1:-}" == --remove ]]; then
    [[ $# -eq 2 ]] || usage
    host=$2
    remove_rules "$host"
    if host_exists "$host"; then
        api DELETE "/objects/host_config/$host" >/dev/null
    fi
    activate
    echo "Removed $host"
    exit 0
fi

[[ $# -eq 2 ]] || usage
host=$1
source_file=$(realpath "$2")
[[ -f "$source_file" ]] || { echo "ERROR: $2 is not a file" >&2; exit 1; }

# Scripts are recognised by their shebang: on bind mounts from macOS every
# file can look executable.
if [[ "$(head -c 2 "$source_file")" == '#!' ]]; then
    [[ -x "$source_file" ]] || { echo "ERROR: $2 has a shebang but is not executable" >&2; exit 1; }
    command="'$source_file'"
else
    command="cat '$source_file'"
fi

if ! host_exists "$host"; then
    api POST /domain-types/host_config/collections/all \
        "$(jq -n --arg h "$host" '{folder: "/", host_name: $h, attributes: {ipaddress: "127.0.0.1"}}')" >/dev/null
    echo "Created host $host"
fi

remove_rules "$host"
api POST /domain-types/rule/collections/all "$(jq -n --arg h "$host" --arg c "$command" --arg m "$(rule_marker "$host")" '{
    ruleset: "datasource_programs",
    folder: "/",
    properties: {disabled: false, description: $m},
    value_raw: ($c | tojson),
    conditions: {host_name: {match_on: [$h], operator: "one_of"}}
}')" >/dev/null
echo "Agent output of $host: $command"

activate

echo
echo "Next:"
echo "  cmk -d $host"
echo "  cmk -vI --detect-plugins=<plugin> $host"
echo "  cmk -v --detect-plugins=<plugin> $host"
