
import anthropic
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
deepseek_client = OpenAI( api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com" )

def call_openai_chat(model, prompt, return_usage=False):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt}
    ]

    completion = client.chat.completions.create(
        model=model,
        messages=messages
    )

    content = completion.choices[0].message.content
    print(content)

    if return_usage:
        return content, completion.usage.model_dump(), completion
    return content

def call_deepseek_chat(model, prompt, return_usage=False):
    messages = [
        {"role": "user", "content": prompt}
    ]

    completion = deepseek_client.chat.completions.create(
        model=model,
        messages=messages
    )

    content = completion.choices[0].message.content
    reasoning = completion.choices[0].message.reasoning_content

    print("=== REASONING CONTENT ===")
    print(reasoning)
    print("=== FINAL ANSWER ===")
    print(content)

    if return_usage:
        return content, {}, reasoning
    return content




def call_anthropic_claude(model, prompt, return_usage=False):
   
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model,
        max_tokens=400,  
        thinking={
            "type": "enabled",
            "budget_tokens": 1000  
        },
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    content = response.content[0].text.strip()

    print("=== CLAUDE RESPONSE ===")
    print(content)

    if return_usage:
        return content, {}, content  
    return content





