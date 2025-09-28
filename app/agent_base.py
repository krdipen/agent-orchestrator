from typing import Any, Dict

class AgentBase:
    async def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
