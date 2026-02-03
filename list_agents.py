
import requests
import os

# Try to get agents from the local backend
try:
    response = requests.get("http://localhost:8000/agents")
    if response.status_code == 200:
        agents = response.json()
        print(f"Found {len(agents)} agents:")
        for agent in agents:
            print(f"- Key: {agent.get('key')}, Name: {agent.get('name')}")
    else:
        print(f"Failed to fetch agents: {response.status_code} {response.text}")
except Exception as e:
    print(f"Error fetching agents: {e}")
