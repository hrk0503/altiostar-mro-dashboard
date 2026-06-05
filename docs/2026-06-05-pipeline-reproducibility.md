# MRO Pipeline Reproducibility Guide

This guide provides step-by-step instructions on how to set up, configure, run, and verify the AltioStar MRO RL training and evaluation pipeline from a fresh clone of the repository.

---

## 1. Prerequisites & Installation

Ensure you have **Python 3.10 or higher** installed.

### Step 1: Clone the Repository
```bash
git clone https://github.com/LifeAtlas/altiostar-tokyo-mro.git
cd altiostar-tokyo-mro
```

### Step 2: Set Up a Virtual Environment (Recommended)
You can use either the standard `venv` library or the high-performance `uv` package manager.

**Using standard `venv`:**
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate
```

**Using `uv` (faster dependency resolution):**
```bash
pip install uv
uv venv
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

### Step 3: Install Dependencies
Install all package requirements defined in the configuration files:
```bash
# Using standard pip:
pip install -r requirements.txt

# Or using uv:
uv pip install -r requirements.txt
```

---

## 2. Pipeline Configuration

All defaults, reward weights, observation scaling factors, and hyperparameters are declared in the project configs:
- **Default Environment Config**: [configs/mro_default.yaml](file:///configs/mro_default.yaml)
- **Scenario Modifiers**: Managed dynamically via the scenario configs.
- **Experiment Configs**: Located in [configs/experiments/](file:///configs/experiments/)

---

## 3. Running the Experiment Pipeline

The pipeline is managed by `run_experiment.py`. It automates the full workflow:
1. Building the `MROEnv` environment with the specified reward variant and scenario.
2. Training the PPO agent (using `stable-baselines3`).
3. Running evaluations across multiple episodes.
4. Exporting metrics to a JSON results file.
5. Logging metrics, parameters, and checkpoints to MLflow.

### Command Reference

#### Option A: Run a Single Experiment
To run a specific combination of a reward variant and a scenario:
```bash
python run_experiment.py --single <VARIANT> <SCENARIO> [options]
```
Example:
```bash
python run_experiment.py --single v2 baseline --timesteps 5000 --eval-episodes 10
```

#### Option B: Run a Master Sweep (All 16 Combinations)
To sweep all 4 reward variants (`v0`, `v1`, `v2`, `v3`) across all 4 scenarios (`baseline`, `rush_hour`, `rain_fade`, `tower_failure`):
```bash
python run_experiment.py --sweep-all --timesteps 50000 --eval-episodes 10
```

#### Option C: Run a Custom Sweep
To sweep a specific subset of variants or scenarios:
```bash
python run_experiment.py --variants v1 v2 --scenarios baseline rush_hour --timesteps 10000
```

#### Option D: Run from a Specific Configuration File
```bash
python run_experiment.py --config configs/experiments/v2_rush_hour.yaml
```

### Argument Reference
- `--single`: Runs one experiment (takes two arguments: `VARIANT` `SCENARIO`).
- `--sweep-all`: Runs all 16 reward variant x scenario experiments.
- `--variants`: Space-separated list of reward variants to run (choices: `v0`, `v1`, `v2`, `v3`).
- `--scenarios`: Space-separated list of scenarios to run (choices: `baseline`, `rush_hour`, `rain_fade`, `tower_failure`).
- `--timesteps`: Number of training steps (default: `5000`).
- `--eval-episodes`: Number of episodes for evaluation (default: `10`).
- `--seed`: Random seed for reproducibility (default: `42`).

---

## 4. Expected Outputs & Verification

When an experiment run finishes successfully, it generates the following directory structure:

```
altiostar-tokyo-mro/
├── checkpoints/
│   └── ppo_<variant>_<scenario>.zip       # Trained PPO agent checkpoints
├── results/
│   ├── experiment_<variant>_<scenario>.json # Metrics for single runs
│   └── sweep_results.json                 # Compiled sweep results (only for sweeps)
├── mlflow.db                              # SQLite database tracking MLflow parameters/metrics
└── mlruns/                                # Directory containing MLflow artifacts (e.g. models)
```

> [!NOTE]
> When running on Google Colab with a GPU runtime, you can edit the computing device dynamically by running:
> `!sed -i 's/device="cpu"/device="auto"/g' run_experiment.py`
> This enables PPO to optimize on CUDA, cutting training time from ~25 minutes down to ~3 minutes per run.

---

## 5. Dashboard Visualization & Local QA

You can run the Streamlit dashboard application locally to inspect and compare results:

```bash
streamlit run src/dashboard/app.py
```

- **Authentication**: When prompted, enter the security password `Winniio-2019`.
- **Viewing Results**: The dashboard dynamically loads files from the [results/](file:///results/) directory. Simply copying new JSON result files here will automatically refresh the metrics tables and plots.

---

## 6. Running Tests

To verify that the environment, scenarios, and pipelines are fully functional and pass regression checks:
```bash
pytest -v
```
All 49+ tests should report green (`passed`).
