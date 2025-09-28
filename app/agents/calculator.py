from ..agent_base import AgentBase
from typing import Dict, Any, List, Union

class Calculator(AgentBase):
    async def run(self, inputs):
        try:
            operation = inputs.get(inputs.get('parent')).get('operation')
            values = inputs.get('values', [])

            if not operation or not isinstance(values, list):
                return {'error': 'Missing or invalid operation/values'}

            resolved_values = []
            for v in values:
                if isinstance(v, str) and v in inputs:
                    if isinstance(inputs[v], dict) and 'result' in inputs[v]:
                        resolved_values.append(inputs[v]['result'])
                    else:
                        resolved_values.append(inputs[v])
                else:
                    resolved_values.append(v)

            result = self._calculate(operation, resolved_values)
            return {'result': result}

        except Exception as e:
            raise e

    def _calculate(self, operation: str, values: List[Union[int, float]]) -> Union[int, float]:
        if not values:
            return 0

        if operation == 'add':
            return sum(values)
        elif operation == 'multiply':
            result = 1
            for v in values:
                result *= v
            return result
        elif operation == 'subtract':
            if len(values) < 2:
                return 0
            result = values[0]
            for v in values[1:]:
                result -= v
            return result
        elif operation == 'divide':
            if len(values) < 2:
                return 0
            result = values[0]
            for v in values[1:]:
                if v == 0:
                    raise ValueError("Division by zero")
                result /= v
            return result
        else:
            raise ValueError(f"Unsupported operation: {operation}")

agent = Calculator()
