from typing import Any, Dict

class AgentBase:
    async def run(self, conf: Dict[str, Any], inputs: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
