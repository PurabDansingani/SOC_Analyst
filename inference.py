
import os
import json
from openai import OpenAI


# Import the logic from our newly created file
from environment import SOCEnv, Action

# ==========================================
# 1. SETUP — Uses mandatory competition env vars
# ==========================================
api_base_url = os.environ.get('API_BASE_URL', 'https://api.openai.com/v1')
model_name = os.environ.get('MODEL_NAME', 'gpt-4o-mini')
hf_token = os.environ.get('HF_TOKEN')

# ==========================================
# 2. INFERENCE SCRIPT
# ==========================================
def run_inference():
    if not hf_token:
         print("ERROR: Please set the 'HF_TOKEN' environment variable (your LLM API key).")
         return

    client = OpenAI(api_key=hf_token, base_url=api_base_url)
    env = SOCEnv()

    tasks = ["easy", "medium", "hard"]

    system_prompt = """You are an expert autonomous SOC Analyst agent.
    Analyze the observations carefully. SPEED IS CRITICAL. 

    PRIORITY RULES & THREAT HUNTING:
    1. MALWARE: If you see a clearly malicious process (e.g., 'malware', 'ransomware') in the active_pids, kill it IMMEDIATELY. Malware encrypts files every second!
    2. DDOS: If a server is under a DDoS attack or CPU is spiking (e.g., 99%), search logs for "syn" or "flood" to find the attacking IP and block it.
    3. BRUTE FORCE: If a brute force attack is underway, search logs for "auth" or "failed" to find the attacker's IP and block it.
    4. MULTIPLE THREATS: If the environment has multiple threats, do not use 'submit_report' until you have explicitly hunted for and neutralized BOTH malware AND malicious IPs.

    TOOL USAGE RULES (STRICT):
    1. search_logs: You must use the exact parameter key "query". DO NOT use 'keyword'. (e.g. {"query": "auth"} or {"query": "syn"})
    2. block_ip: You must use the exact parameter key "ip". DO NOT use 'ip_address'. (e.g. {"ip": "1.2.3.4"})
    3. kill_process: You must use the exact parameter key "pid". Include the full string shown in the active_pids list. DO NOT use 'process_name'. (e.g. {"pid": "malware.exe (pid: 666)"})
    4. isolate_service: You must use the exact parameter key "service". DO NOT use 'service_name'.
    5. submit_report: Use this immediately when you have mitigated ALL threats to end the task. You MUST include the parameter "compromised_ip".

    CRITICAL: You must output ONLY valid JSON containing a "reasoning" string, followed by the "action" object.
    You must match this exact schema:
    {
      "reasoning": "Explain your thought process based on the logs. Is the threat mitigated? What is the next logical step?",
      "action": {
        "tool": "tool_name",
        "params": {"exact_key": "value"}
      }
    }

    - DO NOT wrap your response in markdown code blocks.
    - DO NOT output any text outside of the JSON.
    """

    for task in tasks:
        print(f"[START] task={task} env=SOCEnv model={model_name}")
        obs = env.reset(task)
        done = False
        step_idx = 1
        rewards_list = []
        is_success = False

        chat_history = [{"role": "system", "content": system_prompt}]

        try:
            while not done:
                obs_str = obs.model_dump_json()
                chat_history.append({"role": "user", "content": f"Observation: {obs_str}"})

                try:
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=chat_history,
                        temperature=0.0
                    )
                    agent_output = response.choices[0].message.content or ""
                except Exception as e:
                    # Keep inference resilient when network/auth is unavailable in validators.
                    api_error = str(e).replace('\n', ' ')
                    print(f"[WARNING] llm_call_failed error={api_error}")
                    agent_output = json.dumps({
                        "reasoning": "API call failed; using safe fallback action.",
                        "action": {"tool": "search_logs", "params": {"query": "error"}}
                    })
                chat_history.append({"role": "assistant", "content": agent_output})

                error_msg = "null"
                action_str = ""

                try:
                    response_dict = json.loads(agent_output)
                    action_dict = response_dict.get("action", {})
                    action = Action(**action_dict)
                    # Create a compact, single-line JSON string for the log
                    action_str = json.dumps(action_dict, separators=(',', ':'))
                except Exception as e:
                    action = Action(tool="search_logs", params={"query": "error"})
                    action_str = "parse_error"
                    # Capture exact error string with no newlines
                    error_msg = str(e).replace('\n', ' ')

                obs, reward = env.step(action)
                rewards_list.append(reward.score)

                done_str = "true" if reward.done else "false"
                print(f"[STEP] step={step_idx} action={action_str} reward={reward.score:.2f} done={done_str} error={error_msg}")

                if reward.done:
                    is_success = reward.success
                    done = True
                
                step_idx += 1
        finally:
            # Emitted immediately after env.close() analog
            success_str = "true" if is_success else "false"
            rewards_str = ",".join([f"{r:.2f}" for r in rewards_list])
            print(f"[END] success={success_str} steps={len(rewards_list)} rewards={rewards_str}")

if __name__ == "__main__":
    run_inference()