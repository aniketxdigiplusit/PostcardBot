from langchain_ollama import ChatOllama

# Global Chat Sessions
chat_sessions = {}

# LLM Configuration
llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url="http://192.168.1.16:11434")
sllm = ChatOllama(model="gemma2:2b", temperature=0.7, base_url="http://192.168.1.16:11434")
