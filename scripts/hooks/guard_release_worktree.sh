#!/usr/bin/env bash
set -euo pipefail

payload="$(cat)"

# Extract useful fields from hook payload robustly, regardless of slight schema changes.
readarray -t extracted < <(python3 - <<'PY' "$payload"
import json, sys
raw = sys.argv[1]
try:
    data = json.loads(raw) if raw.strip() else {}
except Exception:
    data = {}

def walk(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            lk = k.lower()
            if lk in {"toolname", "tool", "name"} and isinstance(v, str):
                out["tool_names"].append(v)
            if lk in {"command", "cmd"} and isinstance(v, str):
                out["commands"].append(v)
            if lk == "args" and isinstance(v, list):
                out["commands"].append(" ".join(str(x) for x in v))
            walk(v, out)
    elif isinstance(obj, list):
        for x in obj:
            walk(x, out)

out = {"tool_names": [], "commands": []}
walk(data, out)
print("||".join(out["tool_names"]))
print(" || ".join(out["commands"]))
PY
)

tool_names="${extracted[0]:-}"
command_blob="${extracted[1]:-}"
combined="${tool_names} ${command_blob}"

# Only guard release-related operations.
if ! printf '%s' "$combined" | grep -Eqi '(git[[:space:]]+tag|git[[:space:]]+push|gh[[:space:]]+release|release)'; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Not a release operation."}}'
  exit 0
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Not a git repository."}}'
  exit 0
fi

status_lines="$(git status --porcelain)"
if [[ -z "$status_lines" ]]; then
  echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Working tree clean."}}'
  exit 0
fi

is_allowed_path() {
  local p="$1"
  case "$p" in
    pyproject.toml|uv.lock|CHANGELOG.md|README.md) return 0 ;;
    dist/*|build/*|django_whiteneuron.egg-info/*) return 0 ;;
    docs/reports/*|docs/releases/*) return 0 ;;
    .github/skills/library-build-release/*|.github/prompts/release-notes-from-gitlog.prompt.md) return 0 ;;
    *) return 1 ;;
  esac
}

violations=()
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  # porcelain format: XY<space>PATH or XY<space>OLD -> NEW
  path="${line:3}"
  if [[ "$path" == *" -> "* ]]; then
    path="${path##* -> }"
  fi
  if ! is_allowed_path "$path"; then
    violations+=("$path")
  fi
done <<< "$status_lines"

if [[ ${#violations[@]} -gt 0 ]]; then
  joined="$(printf '%s, ' "${violations[@]}")"
  joined="${joined%, }"
  cat <<EOF
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Release blocked: working tree contains non-release changes: $joined"},"stopReason":"Release blocked by workspace policy: clean unrelated changes before tag/push."}
EOF
  exit 2
fi

echo '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","permissionDecisionReason":"Only release-scope changes detected."}}'
