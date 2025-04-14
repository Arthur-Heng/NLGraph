import openai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY not found in .env file or environment variables")

# Set OpenAI API key

try:
    models = openai.Model.list()
    print("Available Models:")
    for m in models.data:
        print(m.id)
except Exception as e:
    print(f" Failed to list models: {e}")
