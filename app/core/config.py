import os

from dotenv import load_dotenv

load_dotenv()

# Database (MySQL)
DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

# Azure OpenAI (LLM + Whisper STT)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")

# Murf TTS
MURF_API_KEY = os.getenv("MURF_API_KEY", "")

# Azure Blob Storage
AZURE_BLOB_CONNECTION_STRING = os.getenv("AZURE_BLOB_CONNECTION_STRING", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
