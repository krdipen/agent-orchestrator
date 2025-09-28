import asyncio
import uuid
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
        print(f"Created AgentWrapper for {name}")
        print(f"Agent type: {type(agent_instance).__name__}")
        print(f"Agent methods: {dir(agent_instance)}")

    async def run(self, input_data: Dict[str, Any], timeout: Optional[float] = 30.0) -> Any:
        print(f"\n=== AgentWrapper.run({self.name}) ===")
        print(f"Input data: {input_data}")
        print(f"Agent instance: {self.agent}")
        
        try:
            # Create a context for the agent
            ctx = {
                'run_id': getattr(self, 'run_id', ''),
                'node_id': self.name,
                'storage': getattr(self, 'storage', None)
            }
            
            # Extract conf and inputs from input_data
            # For backward compatibility, we'll use the entire input_data as conf
            # and an empty dict for inputs, since the Calculator agent expects specific parameters
            # in the conf dictionary (operation and values)
            conf = input_data
            inputs = {}
            
            print(f"Calling agent.run with conf={conf}, inputs={inputs}, ctx={ctx}")
            
            # Call the agent's run method with the correct signature
            result = await asyncio.wait_for(
                self.agent.run(conf=conf, inputs=inputs, ctx=ctx),
                timeout=timeout
            )
            
            print(f"Agent {self.name} returned: {result}")
            return result
            
        except asyncio.TimeoutError:
            error_msg = f"Agent {self.name} timed out after {timeout} seconds"
            print(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Agent {self.name} failed: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            raise Exception(error_msg)


class Orchestrator:

    def __init__(self, max_concurrent: int = 3, max_retries: int = 2, timeout: int = 30):
        self.agents: Dict[str, Agent] = {}
        self.graph: Dict[str, List[str]] = {}
        self.executions: Dict[str, NodeExecution] = {}
        self.max_retries = max_retries
        self.timeout = timeout
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._execution_lock = asyncio.Lock()

    def register_agent(self, name: str, agent_instance):
        if name in self.agents:
            raise Exception(f"Agent {name} already exists")
        print(f"Registering agent: {name}")
        print(f"Agent type: {type(agent_instance).__name__}")
        print(f"Agent methods: {dir(agent_instance)}")
        self.agents[name] = AgentWrapper(name, agent_instance)
        self.graph[name] = []
        print(f"Registered agent: {name} ({type(agent_instance).__name__})")
        print(f"Agents after registration: {list(self.agents.keys())}")

    def add_dependency(self, from_agent: str, to_agent: str):
        """
        from_agent -> to_agent (to_agent depends on from_agent's result)
        """
        if from_agent not in self.agents or to_agent not in self.agents:
            raise Exception("Both agents must be registered before adding dependency")
        self.graph[from_agent].append(to_agent)

    async def execute_agent(self, agent_type: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single agent with retries and timeout.
        
        Args:
            agent_type: The type of agent to execute
            input_data: Input data for the agent
            
        Returns:
            The result from the agent execution
        """
        if agent_type not in self.agents:
            raise ValueError(f"Agent type '{agent_type}' not found in registered agents. Available agents: {list(self.agents.keys())}")
            
        agent = self.agents[agent_type]
        print(f"Executing agent: {agent_type}")
        
        # Execute the agent with the input data
        result = await agent.run(input_data, timeout=self.timeout)
        
        print(f"Agent {agent_type} completed with result: {result}")
        return result

    async def run(self, nodes: List[Dict], edges: List[Dict], initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the DAG with the given nodes and edges.
        
        Args:
            nodes: List of node definitions with id and agent type
            edges: List of edges defining dependencies
            initial_inputs: Initial inputs for the workflow
            
        Returns:
            Dict containing results from all nodes
        """
        # Generate a unique run ID if not provided
        self.current_run_id = str(uuid.uuid4())
        print(f"\n=== Starting DAG execution {self.current_run_id} ===")
        print(f"Nodes: {[n['id'] for n in nodes]}")
        print(f"Edges: {[(e['from_'], e['to']) for e in edges]}")
        
        # Initialize executions
        node_map = {node['id']: node for node in nodes}
        
        # Build dependency graph
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
            print(f"Node {node_id} depends on: {depends_on}")
        
        # Create a task queue with proper dependencies
        pending = set(node['id'] for node in nodes)
        completed = set()
        results = {}
        
        while pending:
            print(f"\nCurrent state - Pending: {pending}, Completed: {completed}")
            
            # Find all nodes whose dependencies are met
            runnable = []
            for node_id in pending:
                deps = self.executions[node_id].depends_on
                if deps.issubset(completed):
                    runnable.append(node_id)
            
            print(f"Runnable nodes: {runnable}")
            
            if not runnable and pending:
                # Try to find which nodes are causing the deadlock
                blocked = []
                for node_id in pending:
                    missing_deps = self.executions[node_id].depends_on - completed
                    if missing_deps:
                        blocked.append((node_id, missing_deps))
                
                error_msg = "\nDeadlock in dependency graph. Blocked nodes:\n"
                for node_id, deps in blocked:
                    error_msg += f"- {node_id}: waiting for {deps}\n"
                raise Exception(error_msg)
            
            # Execute runnable nodes concurrently
            tasks = []
            for node_id in runnable:
                print(f"Starting execution of node: {node_id}")
                task = asyncio.create_task(
                    self._execute_node(node_id, node_map[node_id], initial_inputs, results)
                )
                tasks.append((node_id, task))
            
            # Wait for all tasks to complete
            for node_id, task in tasks:
                try:
                    result = await task
                    results[node_id] = result
                    completed.add(node_id)
                    pending.remove(node_id)
                    print(f"Completed node {node_id} with result: {result}")
                except Exception as e:
                    print(f"Error in node {node_id}: {str(e)}")
                    self.executions[node_id].status = NodeStatus.FAILED
                    self.executions[node_id].error = str(e)
                    results[node_id] = {'error': str(e)}
                    completed.add(node_id)
                    pending.remove(node_id)
        
        # Format final results
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
        """Execute a single node with proper error handling and result propagation."""
        execution = self.executions[node_id]
        execution.status = NodeStatus.RUNNING
        
        try:
            print(f"\n=== Executing node: {node_id} ===")
            print(f"Node definition: {node_def}")
            
            # Get the agent type from the node definition
            agent_type = node_def.get('agent')
            if not agent_type:
                raise ValueError(f"Node {node_id} is missing 'agent' field")
                
            if agent_type not in self.agents:
                raise ValueError(f"Agent type '{agent_type}' not found in registered agents. Available agents: {list(self.agents.keys())}")
            
            # Prepare inputs from dependencies
            input_data = initial_inputs.copy()
            for dep_id in execution.depends_on:
                if dep_id in results:
                    if isinstance(results[dep_id], dict) and 'result' in results[dep_id]:
                        input_data[dep_id] = results[dep_id]['result']
                    else:
                        input_data[dep_id] = results[dep_id]
            
            print(f"Dependencies resolved: {execution.depends_on}")
            
            # Add node parameters to input
            params = node_def.get('params', {})
            input_data.update(params)
            print(f"Input data: {input_data}")
            
            # Get the agent instance for this node
            agent = self.agents[agent_type]
            print(f"Executing agent: {agent_type} for node {node_id}")
            
            # Execute the agent directly using the wrapper
            result = await agent.run(input_data, timeout=self.timeout)
            
            print(f"Node {node_id} execution result: {result}")
            execution.status = NodeStatus.COMPLETED
            execution.result = result
            
            # Return the result wrapped in a standard format
            return {'result': result, 'node_id': node_id, 'agent_type': agent_type}
            
        except asyncio.CancelledError:
            print(f"Node {node_id} was cancelled")
            execution.status = NodeStatus.FAILED
            execution.error = "Node execution was cancelled"
            raise
            
        except Exception as e:
            error_msg = f"Error in node {node_id}: {str(e)}"
            print(error_msg)
            execution.status = NodeStatus.FAILED
            execution.error = str(e)
            raise Exception(error_msg) from e

    def _get_dependencies(self, agent_name: str) -> List[str]:
        return [dep for dep, children in self.graph.items() if agent_name in children]
