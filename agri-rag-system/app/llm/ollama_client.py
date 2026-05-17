import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

MODEL_NAME = "qwen3.5:latest"

def ask_ollama(prompt):

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(
        OLLAMA_URL,
        json=payload
    )

    data = response.json()

    return data["response"]