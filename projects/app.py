import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
from tavily import TavilyClient
import chromadb
from sentence_transformers import SentenceTransformer
import os
import json
from datetime import datetime
from pypdf import PdfReader
import sys

# Fix the importlib hack - import directly
sys.path.append("C:/AKAI/tools")
from agent_tools import TOOLS, TOOL_MAP

load_dotenv("C:/AKAI/config/.env")

# Workspace configuration
WORKSPACES = ["General", "Job Search", "Poker Solver", "Business"]
WORKSPACE_BASE_PATH = "C:/AKAI/workspaces"

# Knowledge base paths
KNOWLEDGE_PATH = "C:/AKAI/models/knowledge"
DB_PATH = "C:/AKAI/models/chromadb"

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
chroma_client = chromadb.PersistentClient(path=DB_PATH)
collection = chroma_client.get_or_create_collection("knowledge")

def get_workspace_path(workspace_name):
    """Convert workspace name to directory name"""
    return workspace_name.lower().replace(" ", "_")

def load_system_prompt(workspace_name):
    """Load system prompt from workspace directory"""
    workspace_dir = get_workspace_path(workspace_name)
    prompt_path = os.path.join(WORKSPACE_BASE_PATH, workspace_dir, "system_prompt.txt")
    
    if not os.path.exists(prompt_path):
        # Fallback to general if workspace prompt doesn't exist
        prompt_path = os.path.join(WORKSPACE_BASE_PATH, "general", "system_prompt.txt")
    
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

def load_memory(workspace_name):
    """Load memory from workspace directory"""
    workspace_dir = get_workspace_path(workspace_name)
    memory_path = os.path.join(WORKSPACE_BASE_PATH, workspace_dir, "memory.json")
    
    if not os.path.exists(memory_path):
        # Create default memory structure if file doesn't exist
        default_memory = {"conversations": [], "summary": ""}
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(default_memory, f, indent=2)
        return default_memory
    
    with open(memory_path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(workspace_name, memory):
    """Save memory to workspace directory"""
    workspace_dir = get_workspace_path(workspace_name)
    memory_path = os.path.join(WORKSPACE_BASE_PATH, workspace_dir, "memory.json")
    
    with open(memory_path, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def summarize_conversation(client, messages, model):
    """Summarize conversation for memory"""
    summary_prompt = f"""Summarize this conversation in 3-5 bullet points. 
Focus on: decisions made, facts learned about the user, tasks completed, preferences mentioned.
Be specific and concise. No fluff.

Conversation:
{json.dumps(messages, indent=2)}"""
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": summary_prompt}]
    )
    return response.choices[0].message.content

def needs_search(client, model, user_message):
    """Check if message requires web search"""
    check = client.chat.completions.create(
        model=model,
        messages=[{
            "role": "user",
            "content": f"""Does this message require current/live information from the web to answer well? 
Examples that need search: news, prices, recent events, current data, anything time-sensitive.
Examples that don't: coding help, general knowledge, math, personal tasks.
Reply with just YES or NO.

Message: {user_message}"""
        }]
    )
    return check.choices[0].message.content.strip().upper() == "YES"

def web_search(query):
    """Perform web search using Tavily"""
    results = tavily.search(query=query, max_results=5)
    formatted = []
    for r in results["results"]:
        formatted.append(f"Source: {r['url']}\n{r['content']}")
    return "\n\n".join(formatted)

def chunk_text(text, chunk_size=500, overlap=50):
    """Chunk text for RAG"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def ingest_text(text, filename):
    """Ingest text into knowledge base"""
    chunks = chunk_text(text)
    embeddings = embed_model.encode(chunks).tolist()
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        collection.upsert(
            ids=[f"{filename}_chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": filename}]
        )
    return len(chunks)

def query_knowledge(query, n_results=3):
    """Query knowledge base"""
    embedding = embed_model.encode([query]).tolist()
    results = collection.query(query_embeddings=embedding, n_results=n_results)
    if not results["documents"][0]:
        return None
    chunks = results["documents"][0]
    sources = [m["source"] for m in results["metadatas"][0]]
    formatted = []
    for chunk, source in zip(chunks, sources):
        formatted.append(f"Source: {source}\n{chunk}")
    return "\n\n".join(formatted)

# Streamlit app
st.set_page_config(page_title="AKAI", page_icon="🤖", layout="centered")
st.title("🤖 AKAI")

# --- Sidebar ---
# Workspace selector
st.sidebar.markdown("### 🗂️ Workspace")
workspace = st.sidebar.selectbox("Select workspace", WORKSPACES, key="workspace_selector")

# Initialize session state for workspace
if "current_workspace" not in st.session_state:
    st.session_state.current_workspace = workspace

# Check if workspace changed
if st.session_state.current_workspace != workspace:
    st.session_state.current_workspace = workspace
    # Clear chat when switching workspaces
    if "messages" in st.session_state:
        del st.session_state["messages"]
    st.rerun()

# Model selector
model_choice = st.sidebar.selectbox(
    "Choose your model",
    ["DeepSeek V3", "DeepSeek R1", "Ollama Mistral"]
)

# Initialize client based on model choice
if model_choice in ["DeepSeek V3", "DeepSeek R1"]:
    client = OpenAI(
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        base_url="https://api.deepseek.com"
    )
    model = "deepseek-chat" if model_choice == "DeepSeek V3" else "deepseek-reasoner"
else:
    client = OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")
    model = "mistral"

# Save session button
if st.sidebar.button("💾 Save & Summarize Session"):
    if st.session_state.get("messages"):
        memory = load_memory(workspace)
        summary = summarize_conversation(client, st.session_state.messages, model)
        memory["conversations"].append({
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "model": model_choice,
            "summary": summary
        })
        memory["conversations"] = memory["conversations"][-20:]
        save_memory(workspace, memory)
        st.sidebar.success(f"Session saved to {workspace} workspace!")

st.sidebar.markdown("---")
agent_mode = st.sidebar.toggle("🤖 Agent Mode", value=False)
if agent_mode:
    st.sidebar.warning("⚠️ Agent can read/write files and run code in C:/AKAI")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📚 Knowledge Base")

uploaded_file = st.sidebar.file_uploader("Upload a file", type=["txt", "pdf", "md"])
if uploaded_file and st.sidebar.button("➕ Ingest File"):
    with st.spinner(f"Ingesting {uploaded_file.name}..."):
        if uploaded_file.name.endswith(".pdf"):
            reader = PdfReader(uploaded_file)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        else:
            text = uploaded_file.read().decode("utf-8")

        chunks = ingest_text(text, uploaded_file.name)

        save_path = os.path.join(KNOWLEDGE_PATH, uploaded_file.name)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.sidebar.success(f"✅ {chunks} chunks ingested!")

st.sidebar.markdown("---")
kb_files = [f for f in os.listdir(KNOWLEDGE_PATH) if f.endswith((".txt", ".pdf", ".md"))]
if kb_files:
    st.sidebar.markdown("**Files in knowledge base:**")
    for f in kb_files:
        st.sidebar.caption(f"📄 {f}")
else:
    st.sidebar.caption("No files ingested yet.")

# --- Chat ---
# Initialize chat with workspace context
if "messages" not in st.session_state:
    system_prompt = load_system_prompt(workspace)
    memory = load_memory(workspace)
    
    # Add workspace context to system prompt
    workspace_context = f"\n\nCURRENT WORKSPACE: {workspace}\n"
    if workspace != "General":
        workspace_context += f"Context: You are now in the '{workspace}' workspace. Focus on topics relevant to this workspace.\n"
    
    if memory["conversations"]:
        recent = memory["conversations"][-5:]
        memory_text = "\n\n".join([f"[{c['date']}]\n{c['summary']}" for c in recent])
        full_prompt = f"{system_prompt}{workspace_context}\n\nRECENT CONVERSATION HISTORY:\n{memory_text}"
    else:
        full_prompt = f"{system_prompt}{workspace_context}"
    
    st.session_state.messages = [{"role": "system", "content": full_prompt}]

# Display current workspace
st.markdown(f"**Current workspace:** `{workspace}`")

# Display chat messages
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Say something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        reply_placeholder = st.empty()
        full_reply = ""
        messages_to_send = st.session_state.messages.copy()

        # RAG
        rag_results = query_knowledge(prompt)
        if rag_results:
            messages_to_send.append({
                "role": "user",
                "content": f"Relevant info from your knowledge base:\n\n{rag_results}\n\nUse this if relevant to answer: {prompt}"
            })

        # Web search
        if model_choice != "Ollama Mistral" and needs_search(client, model, prompt):
            reply_placeholder.markdown("🔍 Searching the web...")
            search_results = web_search(prompt)
            messages_to_send.append({
                "role": "user",
                "content": f"Web search results:\n\n{search_results}\n\nNow answer: {prompt}"
            })

        # Agent mode
        if agent_mode and model_choice != "Ollama Mistral":
            response = client.chat.completions.create(
                model=model,
                messages=messages_to_send,
                tools=TOOLS,
                tool_choice="auto"
            )

            while response.choices[0].finish_reason == "tool_calls":
                tool_calls = response.choices[0].message.tool_calls
                messages_to_send.append(response.choices[0].message)

                for tool_call in tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)

                    if fn_name in ["write_file", "run_python"]:
                        reply_placeholder.markdown(f"⚠️ Agent wants to **{fn_name}**:\n```\n{json.dumps(fn_args, indent=2)}\n```")

                    result = TOOL_MAP[fn_name](**fn_args)
                    reply_placeholder.markdown(f"🔧 `{fn_name}` → {result[:100]}...")

                    messages_to_send.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })

                response = client.chat.completions.create(
                    model=model,
                    messages=messages_to_send,
                    tools=TOOLS,
                    tool_choice="auto"
                )

            full_reply = response.choices[0].message.content or ""
            reply_placeholder.markdown(full_reply)

        else:
            stream = client.chat.completions.create(
                model=model,
                messages=messages_to_send,
                stream=True
            )

            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_reply += delta
                reply_placeholder.markdown(full_reply + "▌")

            reply_placeholder.markdown(full_reply)

    st.session_state.messages.append({"role": "assistant", "content": full_reply})