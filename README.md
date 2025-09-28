# WandAI — Multi-Agent Task Solver (Challenge 1)

## Overview

A lightweight prototype demonstrating an orchestrator for isolated agents that can pass results, run concurrently, allow retries, have timeouts, support plugins. The orchestrator also exposes REST APIs to manage agents and tasks.

Built with FastAPI (Python 3.11.13)

## How to Run

1. Create venv + install
<br> python -m venv .venv
<br> source .venv/bin/activate
<br> pip install -r requirements.txt

2. Start the server
<br> uvicorn app.main:app --reload --port 8000

## Docker Setup

1. Build the image
<br> docker build -t agent-orchestrator:latest .

2. Run the container
<br> docker run -p 8000:8000 agent-orchestrator:latest

## Test

1. Run demo script (will POST a sample DAG and poll)
<br> bash demo.sh

## Design Decisions & Trade-offs

1. In-memory storage due to 24h time constraint (not durable across restarts).
2. Single-process asyncio-based orchestrator (no distributed queue).
3. Simple retry and timeout policy per node.
4. Dynamic agent loading by module name for pluggability.

## API

1. POST /runs — submit task
2. GET /runs/{run_id} — get status & results for the task id
3. POST /runs — get details of all tasks
