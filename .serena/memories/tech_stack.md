# Tech stack

- **Python 3.13**, the only version used. Both GitHub workflows pin 3.13.
- **venv at `venv/`** (git-ignored). The project itself is not installed; `export PYTHONPATH=.` from
  the repo root makes the `src.` imports resolve (`mem:core`).
- **`requirements.txt` is fully pinned** and mixes runtime and dev tools. Add new dependencies there
  with an exact `==` pin. No test runner or type checker is installed; Pylance/pyright is run from the editor
  (or `npx -y pyright`).

| package | why it is here |
|---|---|
| `numpy` | grids, reservation tables, RNG (`default_rng`), statistics |
| `scipy` | `linear_sum_assignment` for the agent↔task assignment |
| `matplotlib` | simulation frames (`visualization.py`) and all paper figures |
| `pandas`, `seaborn` | analysis summaries and plots (efficiency benchmark, the legacy sweep, figures) |
| `imageio` | GIF assembly in `visualization.make_gif` |
| `tqdm` | progress bars in the long analyses |
| `pylint` | lint gate (`mem:task_completion`) |

`black` is present in the venv but not pinned in `requirements.txt`. CI formats with
`psf/black@stable`, so the local version can drift from CI.
