import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
completion = client.chat.completions.create(
  model="o3-mini-2025-01-31",
  messages=[
    {"role": "user", "content": "Hello, what is 2+2?"}
  ]
)
print(completion.choices[0].message.content)
