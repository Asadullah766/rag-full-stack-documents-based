# app/memory_manager.py

from langchain.memory import ConversationBufferMemory

# This memory will store chat history during session
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

def get_memory():
    """Return current conversation memory."""
    return memory

def add_to_memory(user_input: str, ai_output: str):
    """Save a user input and model output pair into memory."""
    memory.save_context({"input": user_input}, {"output": ai_output})
