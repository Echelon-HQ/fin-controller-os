# Financial Controller

A deterministic, configuration-driven financial controller engine and a vendor-neutral orchestration layer.

---

## Quick overview

- **Phase 1**: ingestion, classification, envelope aggregation, minimal rules engine, `daily_run` console runner.
- **Phase 2**: obligations, obligation buffer rules, recommendation engine, daily digest, append-only JSONL controller log.
- **Phase 3**: orchestration adapter with tool schemas and an example OpenAI agent runner (tool-style functions).

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









