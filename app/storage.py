from typing import Dict, Any
import asyncio

class InMemoryStorage:
    def __init__(self):
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def create_run(self, run_id: str, spec: Dict[str, Any]):
        async with self._lock:
            self._runs[run_id] = {
                'spec': spec,
                'status': 'RUNNING',
                'nodes': {},
                'artifacts': {}
            }

    async def set_node_result(self, run_id: str, node_id: str, result: Dict[str, Any]):
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return
            run['nodes'][node_id] = result

    async def get_run(self, run_id: str):
        async with self._lock:
            return self._runs.get(run_id)

    async def set_status(self, run_id: str, status: str):
        async with self._lock:
            run = self._runs.get(run_id)
            if run:
                run['status'] = status

    async def add_artifact(self, run_id: str, name: str, data: bytes):
        async with self._lock:
            run = self._runs.get(run_id)
            if run:
                run['artifacts'][name] = data

    async def cancel_run(self, run_id: str) -> bool:
        async with self._lock:
            run = self._runs.get(run_id)
            if not run:
                return False
            if run['status'] in ('COMPLETED','FAILED'):
                return False
            run['status'] = 'CANCELLED'
            return True
