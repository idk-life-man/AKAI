from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv("C:/AKAI/config/.env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-reasoner",
    messages=[
        {"role": "user", "content": "Say hello and tell me what model you are."}
    ]
)

print(response.choices[0].message.content)