import os
import anthropic
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    messages=[
    {"role": "user", "content": "Hello, what is 2+2?"}
  ]
)

print(response)
