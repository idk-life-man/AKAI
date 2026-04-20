import os
import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

KNOWLEDGE_PATH = "C:/AKAI/models/knowledge"
DB_PATH = "C:/AKAI/models/chromadb"

model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=DB_PATH)
collection = client.get_or_create_collection("knowledge")

def chunk_text(text, chunk_size=500, overlap=50):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def ingest_file(filepath):
    filename = os.path.basename(filepath)
    ext = filepath.lower().split(".")[-1]

    print(f"Ingesting {filename}...")

    if ext == "pdf":
        reader = PdfReader(filepath)
        text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist()

    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        collection.upsert(
            ids=[f"{filename}_chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk],
            metadatas=[{"source": filename}]
        )

    print(f"Done — {len(chunks)} chunks ingested from {filename}")

if __name__ == "__main__":
    for file in os.listdir(KNOWLEDGE_PATH):
        if file.endswith((".txt", ".pdf", ".md")):
            ingest_file(os.path.join(KNOWLEDGE_PATH, file))
    print("\nAll files ingested!")