from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

BASE_DIR = Path(__file__).resolve().parent.parent

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

db = Chroma(
    persist_directory=str(BASE_DIR / "chroma_db"),
    embedding_function=embeddings
)

question = "What is the vision and mission of MITS Gwalior?"

results = db.similarity_search(
    question,
    k=5,
    filter={"type": "website"}
)

for i, doc in enumerate(results, 1):
    print(f"\nResult {i}")
    print("Title:", doc.metadata.get("title"))
    print("URL:", doc.metadata.get("source"))
    print("Content:", doc.page_content[:500])