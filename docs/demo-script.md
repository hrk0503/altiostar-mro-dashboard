# 2-Minute Demo Script — Soumyadeep

## Step 1 — Fresh CSV in (0:00–0:20)
"We start with raw operator CSV data — site database, 
neighbor relations, and PM counters at relation level. 
No preprocessing needed."

Run:
python scripts/generate_relation_pm.py

## Step 2 — Train (0:20–0:50)
"The pipeline automatically trains a PPO RL agent 
on this data. The agent learns to adjust CIO values 
per neighbor pair to maximize handover success rate."

Run:
python run_experiment.py --single v2 baseline --seed 42

## Step 3 — Evaluate + Ship Gate (0:50–1:20)
"After training, the ship gate automatically checks 
if the model meets client targets — HO success above 
99% and ping-pong below 5%. No manual checking needed."

Show: results/experiment_v2_baseline.json

## Step 4 — Dashboard (1:20–2:00)
"Results are automatically synced to the Streamlit 
dashboard. You can switch scenarios, compare 
before/after KPIs, and see neighbor-level recommendations."

Open: https://altiostar-mro-dashboard.streamlit.app