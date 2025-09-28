import httpx
from ..agent_base import AgentBase

class DataFetcher(AgentBase):
    async def run(self, conf, inputs, ctx):
        url = conf.get('url')
        if not url:
            return {'error': 'missing url'}
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url)
            return {
                'status_code': r.status_code,
                'text': r.text,
                'json': None
            }

agent = DataFetcher()
