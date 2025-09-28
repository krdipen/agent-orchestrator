# WandAI — Multi-Agent Task Solver (Challenge 1)

## Overview

A lightweight prototype demonstrating an orchestrator for isolated agents that can pass results, run concurrently, allow retries, have timeouts, support plugins. The orchestrator also exposes REST APIs to manage agents and tasks.

Built with FastAPI (Python 3.11.13)

## How to run

1. Create venv + install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

2. Start the server
uvicorn app.main:app --reload --port 8000

3. Run demo script (will POST a sample DAG and poll)
bash demo_script.sh

## Design decisions & trade-offs

1. In-memory storage due to 24h time constraint (not durable across restarts).
2. Single-process asyncio-based orchestrator (no distributed queue).
3. Simple retry and timeout policy per node.
4. Dynamic agent loading by module name for pluggability.

## API

1. POST /runs — submit task
2. GET /runs/{run_id} — get status & results for the task id
3. POST /runs — get details of all tasks
