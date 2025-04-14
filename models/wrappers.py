# models/wrappers.py

import anthropic
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    print("=== RAW RESPONSE ===")
    print(completion)

    if return_usage:
        return content, completion.usage.model_dump(), completion
    return content



def call_anthropic_claude(model_name, prompt, temperature=0.7, max_tokens=400):
    """
    Uses Anthropic Claude 3 (e.g., claude-3-opus-20240229) to generate a response.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model=model_name,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    return response.content[0].text.strip()


def call_gemini(model, prompt, temperature=0.7, max_tokens=400):
    """
    Stub for Gemini via Google Generative AI SDK.
    """
    # import google.generativeai as genai
    # genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    # model = genai.GenerativeModel('gemini-pro')
    # response = model.generate_content(...)
    # return response.text
    raise NotImplementedError("Gemini API wrapper not yet implemented.")

