#!/usr/bin/env bash
# prerelease-check.sh: the cheapest safety pass before an agent-built product meets strangers.
#
# Teaches: Section 12 reports that a passive scan of 5,600 public vibe-coded applications found more
# than 2,000 vulnerabilities and over 400 exposed secrets (Escape, 2026). Four free scanners catch the
# commonest leaks and known-vulnerable packages;
# this script runs each one that is installed, says how to install the others, and ends with the
# short list of questions no scanner answers.
# Limits: scanners find known patterns only. A clean run is a floor, not a security review.
# Usage: bash tools/prerelease-check.sh [path-to-project]     (default: current folder)
# Exit code: 0 if every installed scanner passed, 1 if any reported a problem.
# Licence: MIT
set -u
TARGET="${1:-.}"
cd "$TARGET" || { echo "no such folder: $TARGET"; exit 2; }
FAILED=0
SKIPPED=0

run() {  # run <name> <install hint> <command...>
  local name="$1" hint="$2"; shift 2
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "[skip] $name is not installed. Install: $hint"
    SKIPPED=$((SKIPPED + 1))
    return
  fi
  echo "[run ] $name"
  if "$@"; then echo "[ ok ] $name"; else echo "[FAIL] $name reported problems (see above)"; FAILED=1; fi
}

run "gitleaks (secrets in files and history)" "brew install gitleaks, or see github.com/gitleaks/gitleaks" \
  gitleaks detect --source . --no-banner --redact
if ls requirements*.txt pyproject.toml >/dev/null 2>&1; then
  run "pip-audit (known-vulnerable Python packages)" "python3 -m pip install pip-audit" pip-audit
fi
if [ -f package.json ]; then
  run "npm audit (known-vulnerable Node packages)" "comes with Node.js" npm audit --audit-level=high
fi
run "semgrep (risky code patterns)" "python3 -m pip install semgrep" semgrep scan --config auto --error --quiet

cat <<'EOF'

Questions no scanner answers (write the answers in the release notes):
  1. Which secrets does the product hold, and could a user's input make it print one?
  2. What does it do with users' data, where is the data stored, and who can delete it?
  3. What happens when a step fails halfway: is anything sent, paid or deleted twice?
  4. Is there a way back (rollback) for the last release, and has it been tried once?
  5. Who answers when it breaks, by name, and how do users reach that person?
  6. Which actions are irreversible, and does each one ask for a confirmation?
EOF
echo
echo "scanners skipped: $SKIPPED; result: $([ $FAILED -eq 0 ] && echo 'no problems reported' || echo 'problems reported')"
exit $FAILED
