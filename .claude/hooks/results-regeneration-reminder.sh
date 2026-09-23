#!/usr/bin/env bash
# Stop hook: remind the user to regenerate the tracked results after simulation code changed.
#
# results/<analysis>/ holds the data the paper figures are rendered from and must always match
# the current code. The analyses are slow, so they are never re-run automatically; instead this
# hook shows a (non-blocking) reminder after every turn while src/**/*.py has uncommitted changes
# whose affected results/<analysis>/ directories have not been regenerated yet.
#
# Mapping (see the analysis_and_figures memory):
#   simulation and planner modules (everything in src/ except the ones below) -> all four analyses
#   src/scripts/<analysis>.py                                                  -> that analysis
#   src/scripts/{karma_influence_sweep,visualize_simulation,performance_tracking}.py,
#   src/simulation/visualization.py                                            -> none
# Self-terminating: once every affected directory has uncommitted changes (or the work is
# committed), the hook is silent.
set -euo pipefail

analyses="efficiency_benchmark time_distribution karma_influence karma_influence_tradeoffs"

repo="${CLAUDE_PROJECT_DIR:-$(pwd)}"
status="$(git -C "$repo" status --porcelain --untracked-files=all 2>/dev/null || true)"
[ -z "$status" ] && exit 0

affected=""
while IFS= read -r line; do
  [ -z "$line" ] && continue
  path="${line:3}"
  path="${path##* -> }"
  case "$path" in
    src/scripts/karma_influence_sweep.py | src/scripts/visualize_simulation.py | \
      src/scripts/performance_tracking.py | src/simulation/visualization.py) ;;
    src/scripts/*.py) name="${path#src/scripts/}"; affected="$affected ${name%.py}" ;;
    src/*.py) affected="$affected $analyses" ;;
  esac
done <<EOF
$status
EOF
[ -z "$affected" ] && exit 0

pending=""
for name in $(printf '%s\n' $affected | sort -u); do
  printf '%s\n' "$status" | grep -q " results/$name/" || pending="$pending $name"
done
[ -z "$pending" ] && exit 0

pending="$(echo $pending | sed 's/ /, /g')"
cat <<JSON
{"systemMessage":"Reminder: simulation code changed but results/ was not regenerated for ${pending}. Before finalising this iteration, let Claude re-run the affected analyses (./venv/bin/python src/scripts/<analysis>.py) and re-render the figures."}
JSON
exit 0
