from openai import OpenAI
import os

_client = None

def get_client():
    """Get or create the OpenAI client, ensuring API key is loaded from environment."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        _client = OpenAI(api_key=api_key)
    return _client

def summarize_text(text):
    client = get_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a scientific research assistant."},
            {"role": "user", "content": f"Summarize this research abstract clearly:\n\n{text}"}
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content  