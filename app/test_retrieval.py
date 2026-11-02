from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

print("Loading Chroma database...")
vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings,
)

print("\nChecking database...")
data = vectorstore.get()
print("Number of stored chunks:", len(data["ids"]))

question = "When is Mid Sem Exam I?"
print("\nQuestion:", question)

results = vectorstore.similarity_search(question, k=3)
print("\nNumber of retrieved documents:", len(results))

for i, doc in enumerate(results, 1):
    print(f"\n--- RESULT {i} ---")
    print(doc.page_content)