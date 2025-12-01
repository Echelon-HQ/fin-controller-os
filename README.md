# Financial Controller

A small, well-structured, configuration-driven financial controller engine and a minimal orchestration layer.
This repository contains a deterministic engine (ingestion, classification, envelope aggregation, rules, recommendations,
digest generation, and an append-only controller log) and a vendor-neutral orchestration layer for building agents.

---

## Status

- Phase 1: Core ingestion, classification, envelope aggregation, minimal rules engine, `daily_run` (console).
- Phase 2: Obligations, extended rules, recommendation engine, daily digest, append-only JSONL controller log.
- Phase 3: Orchestration adapter + tool schemas and a simple OpenAI-based example runner (agent glue lives in `orchestration/`).

---

## Repository layout
```
financial_controller/

├─ controller/

│ ├─ init.py

│ ├─ models.py

│ ├─ config_loader.py

│ ├─ ingestion.py

│ ├─ classification.py

│ ├─ rules.py

│ ├─ recommendations.py

│ ├─ digest.py

│ ├─ controller_log.py

│ └─ daily_run.py

├─ orchestration/

│ ├─ init.py

│ ├─ tool_schemas.py

│ ├─ controller_adapter.py

│ ├─ agent_prompts.py

│ └─ agent_runner.py

├─ config/

│ ├─ accounts.json

│ ├─ envelopes.json

│ ├─ obligations.json

│ ├─ rules.json

│ └─ classification.json

├─ data/

│ └─ transactions.csv

├─ log/

│ └─ controller_log.jsonl

├─ tests/

│ ├─ test_ingestion.py

│ ├─ test_rules.py

│ ├─ test_obligations.py

│ └─ test_recommendations_and_digest.py

└─ README.md
```
---

## Getting started (local)

### Requirements
- Python 3.10+ (tested with 3.10/3.11)
- Standard library only for engine & tests.
- (Optional for Phase 3) `openai` and `python-dotenv` if you want to run the example agent.

### Create a virtual environment (recommended)
```bash
python3 -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
.venv\Scripts\Activate.ps1
```
- Run the Phase 1 daily evaluation
From project root:
```bash
python -m controller.daily_run \
  --config-dir ./config \
  --data-dir ./data \
  --as-of-date 2025-11-20
```
Run the Phase 2 daily evaluation (includes log)
```bash
python -m controller.daily_run \
  --config-dir ./config \
  --data-dir ./data \
  --log-dir ./log \
  --as-of-date 2025-11-20
```
- Run tests
Run all unit tests:
```bash
python -m unittest discover -s tests
```
---
- Phase 3 (agent orchestration)
The orchestration/ package contains vendor-neutral tool schemas and a controller adapter.

A minimal OpenAI-based runner is included as orchestration/agent_runner.py — it requires openai and python-dotenv and an OPENAI_API_KEY.

Note: Phase 3 is a glue layer only — it never performs numeric logic. The engine (controller/) is the single source of truth.






