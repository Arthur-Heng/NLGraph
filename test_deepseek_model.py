import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
completion = client.chat.completions.create(
  model="deepseek-reasoner",
  messages = [{"role": "user", "content": "9.11 and 9.8, which is greater?"}]
)

print(completion.choices[0].message.reasoning_content)
print(completion.choices[0].message.content)
