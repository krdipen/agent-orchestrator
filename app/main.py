from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .orchestrator import Orchestrator
from .storage import InMemoryStorage
from .agents import data_fetcher, calculator, chart_generator
import asyncio
import uuid

app = FastAPI()
storage = InMemoryStorage()

orchestrator = Orchestrator(
    max_concurrent=3,
    max_retries=2,
    timeout=30
)

# Register available agents
agents = {
    "data_fetcher": data_fetcher.agent,
    "calculator": calculator.agent,
    "chart_generator": chart_generator.agent
}

# Register agents with the orchestrator
for agent_name, agent in agents.items():
    orchestrator.register_agent(agent_name, agent)

class Node(BaseModel):
    id: str
    agent: str
    params: Dict[str, Any] = {}

class Edge(BaseModel):
    from_: str
    to: str

    class Config:
        fields = {"from_": "from", "to": "to"}

class RunRequest(BaseModel):
    nodes: List[Node]
    edges: List[Edge]
    initial_inputs: Dict[str, Any] = {}

class RunStatus(BaseModel):
    run_id: str
    status: str
    results: Dict[str, Any] = {}
    error: Optional[str] = None
    created_at: Optional[float] = None
    updated_at: Optional[float] = None


async def execute_workflow(run_id: str, nodes: List[Node], edges: List[Edge], initial_inputs: Dict[str, Any]):
    try:
        # Convert Pydantic models to dicts
        nodes_dict = [node.dict() for node in nodes]
        edges_dict = [edge.dict() for edge in edges]
        
        # Store initial run state
        await storage.create_run(run_id, {
            'nodes': {node['id']: node for node in nodes_dict},
            'edges': edges_dict,
            'initial_inputs': initial_inputs,
            'status': 'RUNNING'
        })
        
        # Create a new orchestrator instance for this run
        run_orchestrator = Orchestrator(
            max_concurrent=3,
            max_retries=2,
            timeout=30
        )
        
        # Register agents with the new orchestrator
        for agent_name, agent in agents.items():
            run_orchestrator.register_agent(agent_name, agent)
        
        # Execute the workflow
        results = await run_orchestrator.run(
            nodes=nodes_dict,
            edges=edges_dict,
            initial_inputs=initial_inputs
        )
        
        # Update storage with final results
        for node_id, result in results.items():
            await storage.set_node_result(run_id, node_id, result)
        
        await storage.set_status(run_id, 'COMPLETED')
        return results
        
    except Exception as e:
        error_msg = f"Workflow execution failed: {str(e)}"
        await storage.set_status(run_id, 'FAILED')
        return {'error': error_msg}

@app.post("/runs", response_model=dict)
async def create_run(run_request: RunRequest):
    run_id = str(uuid.uuid4())
    
    # Start the workflow execution in the background
    asyncio.create_task(
        execute_workflow(
            run_id=run_id,
            nodes=run_request.nodes,
            edges=run_request.edges,
            initial_inputs=run_request.initial_inputs
        )
    )
    
    return {
        'run_id': run_id,
        'status': 'PENDING',
        'message': 'Workflow execution started'
    }

@app.get("/runs", response_model=Dict[str, Dict[str, Any]])
async def list_runs():
    return await storage.list_runs()

@app.get("/runs/{run_id}", response_model=RunStatus)
async def get_run(run_id: str):
    run = await storage.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    return RunStatus(
        run_id=run_id,
        status=run.get('status', 'UNKNOWN'),
        results=run.get('nodes', {}),
        created_at=run.get('created_at'),
        updated_at=run.get('updated_at')
    )
