from langchain_ollama import ChatOllama
from qdrant_client import QdrantClient
import os

# LLM Configuration
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://192.168.1.16:11434")
llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url=OLLAMA_API_URL)
sllm = ChatOllama(model="gemma2:2b", temperature=0.7, base_url=OLLAMA_API_URL)
# llm = ChatOllama(model="llama3.1:8b", temperature=0.7, base_url="https://0892-49-47-2-255.ngrok-free.app/")
# sllm = ChatOllama(model="gemma2:2b", temperature=0.7, base_url="https://0892-49-47-2-255.ngrok-free.app/")
# QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
# qdrant = QdrantClient(QDRANT_URL)

qdrant = QdrantClient(
    url="http://localhost:6333",     
    timeout=30.0,                   
           
)
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "postcard-openai")