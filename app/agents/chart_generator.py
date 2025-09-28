import io
import matplotlib.pyplot as plt
from ..agent_base import AgentBase

class ChartGenerator(AgentBase):
    async def run(self, conf, inputs, ctx):
        key = conf.get('input_key', 'result')
        val = None
        for p in inputs.values():
            if isinstance(p, dict) and key in p:
                val = p[key]
                break
        if val is None:
            return {'error': 'input key not found'}
        try:
            val = float(val)
        except:
            return {'error': 'input not numeric'}

        fig, ax = plt.subplots()
        ax.bar([0], [val])
        ax.set_ylim(0, max(1, val*1.2))
        ax.set_title(f'value = {val}')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        plt.close(fig)
        buf.seek(0)
        data = buf.read()
        run_id = ctx.get('run_id')
        node_id = ctx.get('node_id')
        storage = ctx.get('storage')
        if storage and run_id and node_id:
            await storage.add_artifact(run_id, f"{node_id}.png", data)
        return {'generated': True, 'bytes': len(data)}

agent = ChartGenerator()
