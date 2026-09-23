# Commands (macOS / Darwin)

Run from the repo root unless noted, with the venv active.

```bash
source venv/bin/activate
# first-time setup (macOS often needs the explicit 3.13 interpreter):
brew install python@3.13 && python3.13 -m venv venv && pip install -r requirements.txt
```

## Gates

```bash
black src src_figures                   # format; CI runs psf/black
./venv/bin/pylint src --errors-only     # the actual gate; must be silent
for n in 1 2 3 4; do ./venv/bin/python src_figures/Figure_$n.py --no-show --output-dir <scratch>; done
```

Render into a scratch dir: the default output dir is `src_figures/` itself, whose PNGs are committed.

## Running simulation code (cwd must be src/: flat imports)

```bash
cd src && ../venv/bin/python _example_visualize_simulation.py      # GIF -> results/animation_<CTRL>.gif
cd src && ../venv/bin/python _analysis_3_karma_influence.py        # edit GRID_SIZE / N_AGENTS first
```

Analyses take minutes to hours and write `log_files/`. **Run them only when the user agrees**
(`mem:task_completion`). Configure them by editing their constants (`mem:analysis_and_figures`).

## Serena upkeep

```bash
uvx --from git+https://github.com/oraios/serena serena memories check   # dangling mem: refs
uvx --from git+https://github.com/oraios/serena serena project index    # refresh symbol cache
```

## Darwin-specific

`stat` is BSD: `stat -f %m file` (not `stat -c %Y`). The `.claude/hooks/*.sh` scripts rely on this.
