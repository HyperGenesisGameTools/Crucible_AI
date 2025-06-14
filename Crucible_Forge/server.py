# Crucible_Forge/server.py
import asyncio
import os
import json
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import agent as CrucibleAgent
import tools as ForgeTools

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI()
origins = [
    "http://localhost", "http://localhost:5500", "http://localhost:8000",
    "http://127.0.0.1:5500", "http://127.0.0.1:8000",
]
app.add_middleware(
    CORSMiddleware, allow_origins=origins, allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), 'web')
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Agent State ---
# This dictionary now holds the entire state of the agent's process
agent_state = {
    "goal": None,
    "master_plan": [],
    "last_observation": "System is ready.",
    "is_running": False
}

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New client connected")
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Client disconnected")
    async def broadcast(self, data: dict):
        """Broadcasts a JSON message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_json(data)

manager = ConnectionManager()

# --- Pydantic Models for API requests ---
class GoalRequest(BaseModel):
    goal: str

# --- Helper to broadcast state updates ---
async def broadcast_state(event_type: str, message: str):
    """Logs, sends a simple text message, and broadcasts the full agent state."""
    logger.info(message)
    # Simple log message for the console/log view
    await manager.broadcast({"type": "log", "data": message})
    # Full state update for the UI to react to
    await manager.broadcast({
        "type": event_type,
        "state": agent_state
    })

# --- Agent Logic Integration ---
async def run_agent_planning(goal: str):
    """Starts the agent by generating the initial master plan."""
    if agent_state["is_running"]:
        await manager.broadcast({"type": "log", "data": "Error: Agent is already running."})
        return

    agent_state["is_running"] = True
    agent_state["goal"] = goal
    agent_state["master_plan"] = []
    agent_state["last_observation"] = "Initializing..."
    
    try:
        await broadcast_state("status_update", "Initializing agent...")
        await asyncio.to_thread(CrucibleAgent.initialize_agent)
        
        await broadcast_state("status_update", f"Generating master plan for goal: {goal}")
        plan = await asyncio.to_thread(CrucibleAgent.create_master_plan, goal)
        agent_state["master_plan"] = plan
        
        await broadcast_state("plan_generated", "✅ Master Plan generated. Ready to execute first step.")
        
    except Exception as e:
        logger.error(f"Error during planning: {e}", exc_info=True)
        agent_state["last_observation"] = f"Error during planning: {e}"
        await broadcast_state("error", f"❌ Error during planning: {e}")
    finally:
        agent_state["is_running"] = False # Ready for user to trigger step

async def run_agent_next_step():
    """Runs the next step of the plan, gets an observation, and re-evaluates."""
    if agent_state["is_running"]:
        await manager.broadcast({"type": "log", "data": "Error: Agent is already busy."})
        return
        
    if not agent_state["master_plan"]:
        await broadcast_state("status_update", "All steps completed! ✅")
        return

    agent_state["is_running"] = True
    
    try:
        # 1. EXECUTE
        task_to_execute = agent_state["master_plan"].pop(0)
        await broadcast_state("status_update", f"🚀 Executing task: {task_to_execute.get('description')}")
        
        observation = await asyncio.to_thread(CrucibleAgent.execute_step, task_to_execute)
        agent_state["last_observation"] = str(observation)
        
        await broadcast_state("observation", f"🔭 Observation received.")
        
        # 2. RE-EVALUATE
        await broadcast_state("status_update", "🤔 Re-evaluating remaining plan...")
        
        new_plan = await asyncio.to_thread(
            CrucibleAgent.reevaluate_and_update_plan,
            goal=agent_state["goal"],
            remaining_plan=agent_state["master_plan"],
            last_observation=agent_state["last_observation"]
        )
        agent_state["master_plan"] = new_plan
        
        if agent_state["master_plan"]:
            await broadcast_state("plan_updated", "✅ Plan re-evaluated. Ready for next step.")
        else:
             await broadcast_state("plan_updated", "✅ Plan re-evaluated. All steps are now complete!")


    except Exception as e:
        logger.error(f"Error during agent cycle: {e}", exc_info=True)
        agent_state["last_observation"] = f"Error during execution: {e}"
        await broadcast_state("error", f"❌ Error during execution: {e}")
    finally:
        agent_state["is_running"] = False


# --- API Endpoints ---
@app.get("/")
async def read_root():
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.post("/api/generate-plan")
async def start_agent_endpoint(request: GoalRequest):
    """Starts the agent planning cycle with a given goal."""
    # Run in background so the HTTP request can return immediately
    asyncio.create_task(run_agent_planning(request.goal))
    return {"message": "Agent planning process initiated. See logs for progress."}

@app.post("/api/execute-next-step")
async def execute_next_step_endpoint():
    """Executes the next step of the current plan."""
    if agent_state["is_running"]:
        return {"error": "Agent is already running a step."}
    asyncio.create_task(run_agent_next_step())
    return {"message": "Agent execution of next step initiated."}

@app.post("/api/stop-agent")
async def stop_agent_endpoint():
    """Stops the agent (basic implementation)."""
    # This is a hard stop, could be improved with graceful shutdown
    agent_state["is_running"] = False
    agent_state["master_plan"] = []
    await broadcast_state("status_update", "Agent execution stopped by user. Plan cleared.")
    return {"message": "Agent stopped."}

# WebSocket endpoint for live state updates
@app.websocket("/ws/log")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial file structure and state on connect
        initial_files = ForgeTools.list_files_recursive.invoke({"directory": "."})
        await websocket.send_json({"type": "file_structure", "data": initial_files})
        await websocket.send_json({"type": "initial_state", "state": agent_state})
        
        while True:
            # Keep connection alive, listening for any client messages (none expected)
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}")

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
