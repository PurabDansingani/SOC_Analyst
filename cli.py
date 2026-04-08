import os
import json
import time
import re
from openai import OpenAI
from environment import SOCEnv, Action


def watch_ai_play():
    print("================================================")
    print("🛡️ WELCOME TO THE AI SOC ANALYST SPECTATOR MODE 🛡️")
    print("================================================")
    
    env = SOCEnv()
    
    # Uses competition-mandatory environment variables
    api_base_url = os.environ.get('API_BASE_URL', 'https://api.openai.com/v1')
    model_name = os.environ.get('MODEL_NAME', 'gpt-4o-mini')
    hf_token = os.environ.get('HF_TOKEN')
    
    if not hf_token:
        print("ERROR: Please set the 'HF_TOKEN' environment variable (your LLM API key).")
        return
    
    client = OpenAI(api_key=hf_token, base_url=api_base_url)
    
    print("\nChoose an attack to unleash on the server:")
    print("1. Brute Force (Easy)")
    print("2. DDoS (Medium)")
    print("3. Ransomware + Brute Force (Hard)")
    
    choice = input("\nEnter choice (1-3): ")
    task_map = {"1": "easy", "2": "medium", "3": "hard"}
    task = task_map.get(choice, "easy")
    
    obs = env.reset(task)
    
    # ---------------------------------------------------------
    # SYNCHRONIZED SYSTEM PROMPT (Matches new inference.py)
    # ---------------------------------------------------------
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
    
    chat_history = [{"role": "system", "content": system_prompt}]
    
    print(f"\n🚀 DEPLOYING AI AGENT TO DEFEND THE NETWORK... STAND BY.\n")
    time.sleep(2)

    done = False
    while not done:
        print("\n" + "="*65)
        print(f"🕒 TICK: {obs.tick_time} | 🚨 STATUS: {obs.task_description}")
        print("💻 SERVER METRICS:")
        for server in obs.servers:
            print(f"  - {server.name} | CPU: {server.cpu_usage}% | Status: {server.status}")
        print("-" * 65)
        print(f"LAST ENVIRONMENT RESULT:\n{obs.last_tool_output}")
        print("="*65)
        
        print("\n[🤖 Agent is analyzing the telemetry...]")
        
        obs_str = obs.model_dump_json()
        chat_history.append({"role": "user", "content": f"Observation: {obs_str}"})

        response = client.chat.completions.create(
            model=model_name,
            messages=chat_history,
            temperature=0.0
        )
        
        agent_output = response.choices[0].message.content
        chat_history.append({"role": "assistant", "content": agent_output})
        
        # ---------------------------------------------------------
        # SYNCHRONIZED PARSER (Handles nested JSON and prints reasoning)
        # ---------------------------------------------------------
        try:
            match = re.search(r'\{.*\}', agent_output, re.DOTALL)
            
            if match:
                cleaned_output = match.group(0)
                response_dict = json.loads(cleaned_output)
                
                # Print the AI's internal thoughts to the terminal!
                if "reasoning" in response_dict:
                    print(f"\n🧠 AI THOUGHT PROCESS:\n{response_dict['reasoning']}\n")
                
                # Extract the nested action object
                action_dict = response_dict.get("action", {})
                action = Action(**action_dict)
                
                print(f"⚡ AGENT EXECUTING: {action.tool} | Parameters: {action.params}")
            else:
                raise ValueError("No JSON brackets {} found in the AI's response.")
                
        except Exception as e:
            print(f"⚠️ AGENT CONFUSED: Failed to parse output.")
            print(f"   [DEBUG] Raw AI Output: {agent_output}") 
            print(f"   [DEBUG] Error: {e}")
            action = Action(tool="search_logs", params={"query": "error"})
            
        obs, reward = env.step(action)
        
        if reward.done:
            print("\n" + "*"*65)
            print("🏁 SIMULATION ENDED 🏁")
            print(f"FINAL CPU STATUS: {obs.servers[0].cpu_usage}%") 
            print(f"Final Score: {reward.score:.2f}")
            print(f"Task Success: {reward.success}")
            print(f"Reason: {reward.message}")
            print("*"*65)
            done = True
            
        time.sleep(2.5) 

if __name__ == "__main__":
    watch_ai_play()