#!/usr/bin/env bash
# Stop hook: remind the user to regenerate log_files/ after simulation code changed.
#
# log_files/analysis_N/ holds the data the paper figures are rendered from and must always match
# the current code. The analyses are slow, so they are never re-run automatically; instead this
# hook shows a (non-blocking) reminder after every turn while src/*.py has uncommitted changes
# whose affected log_files/analysis_N/ directories have not been regenerated yet.
#
# Mapping (see the analysis_and_figures memory):
#   core modules (everything in src/ except the ones below) -> analyses 1-4
#   src/_analysis_N_*.py                                    -> analysis N
#   src/_analysis_4_karma_influence_sweep.py, src/_example_*.py, src/visualization.py -> none
# Self-terminating: once every affected directory has uncommitted changes (or the work is
# committed), the hook is silent.
set -euo pipefail

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"
status="$(git -C "$repo" status --porcelain --untracked-files=all 2>/dev/null || true)"
[ -z "$status" ] && exit 0

affected=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  path="${line:3}"
  path="${path##* -> }"
  case "$path" in
    src/_analysis_4_karma_influence_sweep.py | src/_example_*.py | src/visualization.py) ;;
    src/_analysis_4_*.py) affected="$affected 4" ;;
    src/_analysis_[123]_*.py) n="${path#src/_analysis_}"; affected="$affected ${n%%_*}" ;;
    src/*.py) affected="$affected 1 2 3 4" ;;
  esac
done <<EOF
$status
EOF
[ -z "$affected" ] && exit 0

pending=""
for n in $(printf '%s\n' $affected | sort -u); do
  printf '%s\n' "$status" | grep -q " log_files/analysis_$n/" || pending="$pending $n"
done
[ -z "$pending" ] && exit 0

pending="$(echo $pending | sed 's/ /, /g')"
cat <<JSON
{"systemMessage":"Reminder: simulation code changed but log_files/ was not regenerated for analysis ${pending}. Before finalising this iteration, let Claude re-run the affected analyses (cd src && ../venv/bin/python _analysis_<N>_*.py) and re-render the figures."}
JSON
exit 0
