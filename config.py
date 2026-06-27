import os

# ============================================================
#  CONFIGURATION (edit these)
# ============================================================
CONFIG = {
    # API Keys
    "deepseek_key": os.getenv("DEEPSEEK_API_KEY", "sk-..."),
    "groq_key": os.getenv("GROQ_API_KEY", "gsk_..."),

    # Endpoints
    "deepseek_url": "https://api.deepseek.com/v1/chat/completions",
    "groq_url": "https://api.groq.com/openai/v1/chat/completions",

    # Memory
    "memory_db": os.path.expanduser("~/Atlas/memory.db"),

    # System limits
    "max_dag_nodes": 10,
    "budget": 0.10,               # USD per run

    # Model selection
    "planner_model": "deepseek-reasoner",
    "intent_model": "llama-3.1-8b-instant",   # Groq fast
    "reflector_model": "deepseek-chat",       # optional async
}
