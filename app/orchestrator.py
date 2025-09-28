import asyncio
import traceback
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from enum import Enum

class NodeStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

@dataclass
class NodeExecution:
    id: str
    status: NodeStatus = NodeStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    retries: int = 0
    depends_on: Set[str] = None

class AgentWrapper:

    def __init__(self, name: str, agent_instance):
        self.name = name
        self.agent = agent_instance

    async def run(self, input_data: Dict[str, Any], timeout: Optional[float] = 30.0) -> Any:
        try:
            result = await asyncio.wait_for(
                self.agent.run(inputs=input_data),
                timeout=timeout
            )
            return result

        except asyncio.TimeoutError:
            error_msg = f"Agent {self.name} timed out after {timeout} seconds"
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Agent {self.name} failed: {str(e)}"
            traceback.print_exc()
            raise Exception(error_msg)

class Orchestrator:

    def __init__(self, max_concurrent: int = 3, max_retries: int = 2, timeout: int = 30):
        self.agents: Dict[str, Agent] = {}
        self.executions: Dict[str, NodeExecution] = {}
        self.max_retries = max_retries
        self.timeout = timeout

    def register_agent(self, name: str, agent_instance):
        if name in self.agents:
            raise Exception(f"Agent {name} already exists")
        self.agents[name] = AgentWrapper(name, agent_instance)

    async def run(self, nodes: List[Dict], edges: List[Dict], initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        node_map = {node['id']: node for node in nodes}

        for node in nodes:
            node_id = node['id']
            depends_on = set()
            for edge in edges:
                if edge['to'] == node_id:
                    depends_on.add(edge['from_'])
            self.executions[node_id] = NodeExecution(
                id=node_id,
                depends_on=depends_on
            )

        pending = set(node['id'] for node in nodes)
        completed = set()
        results = {}

        while pending:
            runnable = []
            for node_id in pending:
                deps = self.executions[node_id].depends_on
                if deps.issubset(completed):
                    runnable.append(node_id)
            if not runnable and pending:
                blocked = []
                for node_id in pending:
                    missing_deps = self.executions[node_id].depends_on - completed
                    if missing_deps:
                        blocked.append((node_id, missing_deps))
                error_msg = "\nDeadlock in dependency graph. Blocked nodes:\n"
                for node_id, deps in blocked:
                    error_msg += f"- {node_id}: waiting for {deps}\n"
                raise Exception(error_msg)

            tasks = []
            for node_id in runnable:
                task = asyncio.create_task(
                    self._execute_node(node_id, node_map[node_id], initial_inputs, results)
                )
                tasks.append((node_id, task))
            for node_id, task in tasks:
                try:
                    result = await task
                    results[node_id] = result
                    completed.add(node_id)
                    pending.remove(node_id)
                except Exception as e:
                    completed.add(node_id)
                    pending.remove(node_id)

        return {
            node_id: {
                'status': exec.status.value,
                'result': exec.result,
                'error': exec.error,
                'retries': exec.retries
            }
            for node_id, exec in self.executions.items()
        }

    async def _execute_node(self, node_id: str, node_def: Dict, initial_inputs: Dict, results: Dict) -> Any:
        execution = self.executions[node_id]
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                execution.status = NodeStatus.RUNNING
                execution.retries = attempt

                agent_type = node_def.get('agent')
                if not agent_type:
                    raise ValueError(f"Node {node_id} is missing 'agent' field")

                if agent_type not in self.agents:
                    raise ValueError(f"Agent type '{agent_type}' not found in registered agents. Available agents: {list(self.agents.keys())}")

                input_data = initial_inputs.copy()
                for dep_id in execution.depends_on:
                    if dep_id in results:
                        if isinstance(results[dep_id], dict) and 'result' in results[dep_id]:
                            input_data[dep_id] = results[dep_id]['result']
                        else:
                            input_data[dep_id] = results[dep_id]

                params = node_def.get('params', {})
                input_data.update(params)
                print(f"Input data: {input_data}")

                agent = self.agents[agent_type]
                result = await agent.run(input_data, timeout=self.timeout)
                execution.status = NodeStatus.COMPLETED
                execution.result = result
                return {'result': result, 'node_id': node_id, 'agent_type': agent_type}

            except asyncio.CancelledError:
                execution.status = NodeStatus.FAILED
                execution.error = "Node execution was cancelled"
                raise

            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * (attempt + 1))
                    continue
                error_msg = f"Node {node_id} failed after {self.max_retries} retries: {str(e)}"
                execution.status = NodeStatus.FAILED
                execution.error = error_msg
                raise Exception(error_msg) from last_error
