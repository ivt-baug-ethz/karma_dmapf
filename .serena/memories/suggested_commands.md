# Commands (macOS / Darwin)

Run from the repo root unless noted, with the venv active and `export PYTHONPATH=.` (the `src.` imports need it).

```bash
source venv/bin/activate
# first-time setup (macOS often needs the explicit 3.13 interpreter):
brew install python@3.13 && python3.13 -m venv venv && pip install -r requirements.txt
```

## Gates

```bash
black src figures                       # format; CI runs psf/black
PYTHONPATH=. ./venv/bin/pylint src --errors-only   # the actual gate; must be silent
for n in 1 2 3 4 5; do ./venv/bin/python figures/Figure_$n.py --no-show --output-dir <scratch>; done
```

Render into a scratch dir: the default output dir is `figures/` itself, whose PNGs are committed.

## Running simulation code (repo root, `PYTHONPATH=.`)

```bash
./venv/bin/python src/scripts/visualize_simulation.py   # GIF -> results/animations/animation_<CTRL>.gif
./venv/bin/python src/scripts/karma_influence.py        # edit GRID_SIZE / N_AGENTS first
./venv/bin/python src/scripts/delay_evaluation.py       # both small scenarios, ≈ 9 min on 16 cores
```

Analyses take minutes to hours and write the tracked `results/<analysis>/`. **Run them only when the user agrees**
(`mem:task_completion`). Configure them by editing their constants (`mem:analysis_and_figures`).

## Serena upkeep

```bash
uvx --from git+https://github.com/oraios/serena serena memories check   # dangling mem: refs
uvx --from git+https://github.com/oraios/serena serena project index    # refresh symbol cache
```

## Stopping pooled runs

Killing the parent of a `ProcessPoolExecutor` / `multiprocessing.Pool` leaves its spawned workers
running as orphans (parent PID 1) until their current job ends, which can be hours on 15×15. After
a kill, check and clean up:

```bash
ps -Ao pid,ppid,command | awk '$2 == 1 && /multiprocessing.spawn/'   # orphaned workers
```

Busy-core count: `ps -Ao %cpu,command | awk '/Python/ && $1 > 20' | wc -l`.

## Darwin-specific

`stat` is BSD: `stat -f %m file` (not `stat -c %Y`). The `.claude/hooks/*.sh` scripts rely on this.
