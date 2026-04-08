---
title: SOC Incident Response
emoji: "🛡️"
colorFrom: indigo
colorTo: blue
sdk: docker
pinned: false
---

# 🛡️ SOC Incident Response — OpenEnv

A real-world cybersecurity environment where an AI agent acts as a **SOC (Security Operations Center) analyst** to triage, isolate, and mitigate an active server breach based on system logs.

Built for the [OpenEnv](https://openenv.dev) competition.

---

## 🎯 Problem Statement

An enterprise network is under active attack. The AI agent must analyze telemetry from servers, search through security logs, identify threats, and take decisive action — all under time pressure. Every tick that passes without mitigation causes further damage (encrypted files, degraded services, compromised accounts).

## 🏗️ Environment Design

### Threat Scenarios (Tasks)

| Task | Difficulty | Threats | Success Criteria |
|------|-----------|---------|-----------------|
| `easy` | 🟢 | Brute force SSH attack | Block attacker IP, submit correct report |
| `medium` | 🟡 | DDoS (SYN flood) | Block attacker IP, restore CPU < 50% |
| `hard` | 🔴 | Brute force + Ransomware | Block IP, kill malware process, minimize file encryption |

### Agent Tools

| Tool | Parameters | Description |
|------|-----------|-------------|
| `search_logs` | `{"query": "..."}` | Search security logs for patterns |
| `block_ip` | `{"ip": "x.x.x.x"}` | Add firewall rule to block an IP |
| `kill_process` | `{"pid": "name (pid: N)"}` | Terminate a running process |
| `isolate_service` | `{"service": "..."}` | Isolate a service from the network |
| `submit_report` | `{"compromised_ip": "..."}` | Submit final incident report |

### Scoring

- Each step costs `-0.05` (time pressure)
- Correct actions earn `+0.25` to `+0.50`
- Wrong actions (killing legitimate processes, blocking wrong IPs) penalize heavily
- Final score on `submit_report` depends on threat mitigation status
- Max 15 ticks before automatic failure

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An OpenAI API key (or compatible provider)

### Environment Variables

```bash
export API_BASE_URL="https://api.openai.com/v1"   # LLM API endpoint
export MODEL_NAME="gpt-4o-mini"                     # Model identifier
export HF_TOKEN="sk-your-api-key-here"              # Your API key
```

### Install & Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start the environment server
python server.py
# → Server runs on http://localhost:7860

# Or with uv
uv run server
```

### Run the Inference Script

```bash
python inference.py
```

This runs the AI agent against all 3 tasks (easy, medium, hard) and outputs structured logs:

```
[START] task=easy env=SOCEnv model=gpt-4o-mini
[STEP] step=1 action={"tool":"search_logs","params":{"query":"auth"}} reward=-0.05 done=false error=null
[STEP] step=2 action={"tool":"block_ip","params":{"ip":"103.45.67.89"}} reward=0.45 done=false error=null
[STEP] step=3 action={"tool":"submit_report","params":{"compromised_ip":"103.45.67.89"}} reward=0.45 done=true error=null
[END] success=true steps=3 rewards=-0.05,0.45,0.45
```

### Interactive Spectator Mode

```bash
python cli.py
```

Watch the AI agent defend the network in real-time with colorful terminal output.

---

## 🐳 Docker

```bash
docker build -t soc-openenv .
docker run -p 7860:7860 -e HF_TOKEN=sk-your-key -e API_BASE_URL=https://api.openai.com/v1 -e MODEL_NAME=gpt-4o-mini soc-openenv
```

---

## 📁 Project Structure

```
soc-openenv/
├── openenv.yaml        # OpenEnv environment spec
├── environment.py      # Core environment logic (SOCEnv, Action, Observation, Reward)
├── server.py           # FastAPI server (reset/step/state endpoints)
├── inference.py        # Inference script with structured logging
├── cli.py              # Interactive spectator mode
├── Dockerfile          # HF Spaces deployment
├── pyproject.toml      # uv / pip project config
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Health check (returns 200) |
| `POST` | `/reset` | Reset env with `{"task_id": "easy\|medium\|hard"}` |
| `POST` | `/step` | Execute action `{"tool": "...", "params": {...}}` |
| `GET` | `/state` | Get current observation |

---

## 👤 Author

**Purab Dansingani, Aryan Dalvi, Dhruv Jain**
