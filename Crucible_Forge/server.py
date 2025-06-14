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
import tools as ForgeTools # <-- FIX: Import the tools module

# --- Configuration ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Add CORS Middleware ---
origins = [
    "http://localhost",
    "http://localhost:5500",
    "http://localhost:8000",
    "http://127.0.0.1:5500",
    "http://127.0.0.1:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the 'web' directory to serve static files (HTML, CSS, JS)
static_dir = os.path.join(os.path.dirname(__file__), 'web')
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# --- Agent State ---
agent_state = {
    "plan": None,
    "observations": None,
    "is_running": False,
    "goal": None
}

# --- WebSocket Manager ---
class ConnectionManager:
    """Manages active WebSocket connections."""
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("New client connected")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("Client disconnected")

    async def broadcast(self, message: str):
        """Broadcasts a message to all connected clients."""
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- Pydantic Models for API requests ---
class GoalRequest(BaseModel):
    goal: str

class PlanRequest(BaseModel):
    plan: list

# --- Agent Logic Integration ---
async def log_and_broadcast(message: str):
    """Helper function to log a message and send it to all clients."""
    logger.info(message)
    await manager.broadcast(message)

async def run_agent_cycle(goal: str):
    """Runs a full Plan-Execute-Evaluate cycle for the agent."""
    if agent_state["is_running"]:
        await log_and_broadcast("Error: Agent is already running.")
        return

    agent_state["is_running"] = True
    agent_state["goal"] = goal
    
    try:
        await log_and_broadcast("Initializing agent...")
        await asyncio.to_thread(CrucibleAgent.initialize_agent)
        await log_and_broadcast("Agent initialized.")

        await log_and_broadcast(f"Creating plan for goal: {goal}")
        plan = await asyncio.to_thread(CrucibleAgent.create_plan, goal)
        agent_state["plan"] = plan
        await manager.broadcast(json.dumps({"type": "plan_generated", "plan": plan}))
        await log_and_broadcast("Plan generated. Awaiting approval.")
        
    except Exception as e:
        await log_and_broadcast(f"Error during planning: {str(e)}")
        agent_state["is_running"] = False


async def execute_agent_plan(plan: list):
    """Executes the approved plan and evaluates the result."""
    if not agent_state["is_running"]:
        await log_and_broadcast("Error: Agent is not in a running state to execute a plan.")
        return

    try:
        await log_and_broadcast("Executing approved plan...")
        plan_succeeded, observations = await asyncio.to_thread(CrucibleAgent.execute_plan, plan)
        agent_state["observations"] = observations
        
        await log_and_broadcast("--- Observations ---")
        await log_and_broadcast(observations)
        await log_and_broadcast("--- End of Observations ---")

        if not plan_succeeded:
             await log_and_broadcast("Plan execution failed. Check observations for details.")
             agent_state["is_running"] = False
             return
        
        await log_and_broadcast("Evaluating results...")
        is_goal_achieved = await asyncio.to_thread(CrucibleAgent.evaluate_results, agent_state["goal"], observations)
        
        if is_goal_achieved:
            await log_and_broadcast("🎉 Goal Achieved Successfully! ✅")
        else:
            await log_and_broadcast("Goal not achieved. Review observations to plan next steps.")

    except Exception as e:
        await log_and_broadcast(f"Error during execution/evaluation: {str(e)}")
    finally:
        agent_state["is_running"] = False
        await log_and_broadcast("Agent cycle finished. Ready for new goal.")


# --- API Endpoints ---
@app.get("/")
async def read_root():
    """Serves the main HTML file."""
    return FileResponse(os.path.join(static_dir, 'index.html'))

@app.post("/api/start-agent")
async def start_agent(request: GoalRequest):
    """Starts the agent planning cycle with a given goal."""
    asyncio.create_task(run_agent_cycle(request.goal))
    return {"message": "Agent planning process initiated."}

@app.post("/api/execute-plan")
async def execute_plan_endpoint(request: PlanRequest):
    """Executes the user-approved plan."""
    if not agent_state["is_running"]:
         return {"error": "Agent is not in a running state. Please start with a goal first."}
    asyncio.create_task(execute_agent_plan(request.plan))
    return {"message": "Agent execution process initiated."}

@app.post("/api/stop-agent")
async def stop_agent():
    """Stops the agent (basic implementation)."""
    agent_state["is_running"] = False
    await log_and_broadcast("Agent execution stopped by user.")
    return {"message": "Agent stopped."}

# WebSocket endpoint for live logging
@app.websocket("/ws/log")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial file structure
        # FIX: Call the function from the correct module (ForgeTools)
        initial_files = ForgeTools.list_files_recursive.invoke({"directory": "."})
        await websocket.send_text(json.dumps({"type": "file_structure", "data": initial_files}))
        
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in websocket endpoint: {e}")
        await manager.broadcast(f"Server-side websocket error: {e}")


# This allows running the server with `python server.py`
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
