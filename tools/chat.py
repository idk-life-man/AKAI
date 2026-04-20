from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv("C:/AKAI/config/.env")

print("\nWho do you want to talk to?")
print("1. DeepSeek V3 (everyday)")
print("2. DeepSeek R1 (deep thinking)")
print("3. Ollama Mistral (local/free)")
choice = input("\nEnter 1, 2 or 3: ").strip()

if choice == "1":
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    model = "deepseek-chat"
    name = "DeepSeek V3"
elif choice == "2":
    client = OpenAI(api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com")
    model = "deepseek-reasoner"
    name = "DeepSeek R1"
elif choice == "3":
    client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    model = "mistral"
    name = "Ollama Mistral"
else:
    print("Invalid choice, exiting.")
    exit()

print(f"\nChatting with {name}. Type 'exit' to quit.\n")

history = []

while True:
    user_input = input("You: ").strip()
    if user_input.lower() == "exit":
        print("Bye!")
        break
    
    history.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model=model,
        messages=history
    )
    
    reply = response.choices[0].message.content
    history.append({"role": "assistant", "content": reply})
    print(f"\n{name}: {reply}\n")