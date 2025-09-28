import asyncio
import httpx
import json
import sys
from typing import Dict, Any, List

# Sample DAG configuration
DAG = {
    "nodes": [
        {
            "id": "test_node_1",
            "agent": "calculator",
            "params": {
                "operation": "add",
                "values": [1, 2, 3, 4]
            }
        },
        {
            "id": "test_node_2",
            "agent": "calculator",
            "params": {
                "operation": "multiply",
                "values": [5, 6]
            }
        }
    ],
    "edges": [
        {"from_": "test_node_1", "to": "test_node_2"}
    ],
    "initial_inputs": {}
}

class WorkflowTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def close(self):
        await self.client.aclose()
    
    async def run_workflow(self, dag: Dict[str, Any]) -> Dict[str, Any]:
        """Run a workflow and wait for completion."""
        print("\n=== Starting workflow ===")
        print(f"DAG: {json.dumps(dag, indent=2)}")
        
        # Start the workflow
        response = await self.client.post(
            f"{self.base_url}/runs",
            json=dag
        )
        
        if response.status_code != 200:
            error_msg = f"Failed to start workflow: {response.text}"
            print(error_msg)
            return {"error": error_msg}
        
        run_info = response.json()
        run_id = run_info.get("run_id")
        
        if not run_id:
            error_msg = "No run_id in response"
            print(error_msg)
            return {"error": error_msg}
        
        print(f"\n=== Workflow started with ID: {run_id} ===")
        
        # Poll for results
        max_attempts = 30  # 30 seconds max wait time
        attempt = 0
        last_status = ""
        
        while attempt < max_attempts:
            attempt += 1
            
            try:
                response = await self.client.get(
                    f"{self.base_url}/runs/{run_id}",
                    timeout=5.0
                )
                
                if response.status_code != 200:
                    print(f"Error checking status: {response.text}")
                    await asyncio.sleep(1)
                    continue
                
                status = response.json()
                current_status = status.get("status")
                
                if not current_status:
                    print("No status in response")
                    await asyncio.sleep(1)
                    continue
                
                if current_status != last_status:
                    print(f"\nStatus: {current_status}")
                    last_status = current_status
                else:
                    print(".", end="")
                    sys.stdout.flush()
                
                if current_status in ["COMPLETED", "FAILED"]:
                    print("\n\n=== Workflow completed! ===")
                    print(json.dumps(status, indent=2))
                    return status
                
            except Exception as e:
                print(f"\nError while polling: {str(e)}")
            
            await asyncio.sleep(1)
        
        return {"error": f"Max polling attempts ({max_attempts}) reached"}

async def test_dag():
    print("=== Starting DAG test ===")
    tester = WorkflowTester()
    try:
        result = await asyncio.wait_for(
            tester.run_workflow(DAG),
            timeout=60.0  # 60 second timeout for the entire test
        )
        
        print("\n=== Test completed! ===")
        if result.get("status") == "COMPLETED":
            print("✅ Workflow completed successfully!")
        else:
            print("❌ Workflow failed or did not complete")
            
        print("\nFinal result:")
        print(json.dumps(result, indent=2))
        return result
        
    except asyncio.TimeoutError:
        print("\n❌ Test timed out after 60 seconds")
        return {"error": "Test timed out"}
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        await tester.close()
        print("\n=== Test finished ===")

if __name__ == "__main__":
    asyncio.run(test_dag())
