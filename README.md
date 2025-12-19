# Financial Controller OS

A deterministic, configuration-driven financial controller with a clean orchestration layer and a fully local user interface.

This system is designed to act as a **financial control plane**: it ingests transactions, evaluates rules and obligations, produces daily and weekly digests, runs what-if simulations, and surfaces actionable recommendations — all without relying on cloud services or black-box logic.

---

## High-Level Overview

The Financial Controller OS is composed of three clear layers:

1. **Financial Controller Engine (`controller/`)**  
   Deterministic core responsible for all financial logic.

2. **Orchestration Layer (`orchestration/`)**  
   A stable, JSON-contract-based interface exposing the engine as callable tools.

3. **Interface Layer (`ui/`)**  
   A Streamlit-based local UI for daily use, analysis, and simulation.

Each layer is isolated, testable, and replaceable.

---

## Key Design Principles

- Deterministic by default  
- Configuration-driven  
- Strict separation of concerns  
- Local-first & offline  
- Future-proof orchestration

---

## Repository Structure

```
fin-controller/
├── controller/
├── orchestration/
├── ui/
│   └── app.py
├── config/
├── data/
├── log/
├── tests/
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Running the Application

```bash
python -m streamlit run ui/app.py
```

UI will be available at:

```
http://localhost:8501
```

---

## Configuration

All behavior is driven by JSON files in `config/`.

No logic changes are required to alter financial behavior.

---

## Logs

Daily controller activity is stored in:

```
log/controller_log.jsonl
```

---

## Summary

This repository represents a production-grade financial controller foundation with:
- Deterministic correctness
- Clear abstractions
- Local-first operation
- Reusable orchestration contracts
