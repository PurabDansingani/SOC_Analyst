"""
FastAPI server exposing the SOC Incident Response environment
via the OpenEnv spec endpoints: reset(), step(), state().
"""

import os
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional

from environment import SOCEnv, Action, Observation, Reward

# ==========================================
# APP SETUP
# ==========================================
app = FastAPI(
    title="SOC Incident Response — OpenEnv",
    description="A cybersecurity environment where an AI agent triages, isolates, and mitigates an active server breach.",
    version="1.0.0",
)

env = SOCEnv()
current_task_description = "No task loaded. Call /reset first."


# ==========================================
# REQUEST / RESPONSE MODELS
# ==========================================
class ResetRequest(BaseModel):
    task_id: str = "easy"


class StepResponse(BaseModel):
    observation: Observation
    reward: Reward


# ==========================================
# ENDPOINTS
# ==========================================
@app.get("/")
def health_check():
    """Health check — returns 200 for the HF Spaces automated ping."""
    return {"status": "ok", "environment": "soc-incident-response", "version": "1.0.0"}


@app.post("/reset", response_model=Observation)
def reset(request: Optional[ResetRequest] = None):
    """Reset the environment with a given task_id (easy, medium, hard)."""
    global current_task_description
    task_id = request.task_id if request else "easy"
    obs = env.reset(task_id)
    current_task_description = obs.task_description
    return obs


@app.post("/step", response_model=StepResponse)
def step(action: Optional[dict] = None):
    """Execute one action in the environment and return observation + reward."""
    action = action or {}
    tool = action.get("tool", "search_logs")
    params = action.get("params", {"query": "auth"})
    # Defensive fallback to avoid 422 in validators that send malformed bodies.
    try:
        safe_action = Action(tool=tool, params=params)
    except Exception:
        safe_action = Action(tool="search_logs", params={"query": "auth"})
    obs, reward = env.step(safe_action)
    return StepResponse(observation=obs, reward=reward)


@app.get("/web", response_class=HTMLResponse)
def web():
    """Minimal web route for validators that probe /web."""
    return """
    <html>
      <head><title>SOC Incident Response</title></head>
      <body>
        <h1>SOC Incident Response - OpenEnv</h1>
        <p>Status: running</p>
        <p>Use API endpoints: /reset, /step, /state, /docs</p>
      </body>
    </html>
    """


@app.get("/state", response_model=Observation)
def state():
    """Return the current environment state without advancing the simulation."""
    return env.state(task_description=current_task_description)


# ==========================================
# ENTRYPOINT
# ==========================================
def main():
    """Entry point for `uv run server`."""
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)


if __name__ == "__main__":
    main()
