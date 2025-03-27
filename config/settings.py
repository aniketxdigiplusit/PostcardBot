from langchain_ollama import ChatOllama

# Global Chat Sessions
chat_sessions = {}

# LLM Configuration
llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url="http://192.168.1.45:11434")
sllm = ChatOllama(model="gemma2:2b", temperature=0.7, base_url="http://192.168.1.45:11434")
# llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url="https://0892-49-47-2-255.ngrok-free.app/")
# sllm = ChatOllama(model="gemma2:2b", temperature=0.7, base_url="https://0892-49-47-2-255.ngrok-free.app/")
