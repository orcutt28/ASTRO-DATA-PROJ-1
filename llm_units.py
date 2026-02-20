from openai import OpenAI
import os

client = OpenAI()

def summarize_text(text):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a scientific research assistant."},
            {"role": "user", "content": f"Summarize this research abstract clearly:\n\n{text}"}
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content  