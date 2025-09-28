import httpx
from ..agent_base import AgentBase

class DataFetcher(AgentBase):
    async def run(self, inputs):
        url = inputs.get('url')
        if not url:
            return {'error': 'missing url'}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            return {
                'status_code': r.status_code,
                'operation': r.text,
            }

agent = DataFetcher()
