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

results = db.similarity_search(
    "CSE department faculty members names qualifications research interests",
    k=10,
    filter={"type": "website"}
)

for i, doc in enumerate(results, 1):
    print(f"\n--- Result {i} ---")
    print("Title:", doc.metadata.get("title"))
    print("URL:", doc.metadata.get("source"))
    print(doc.page_content[:1000])