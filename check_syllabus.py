from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

db = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

results = db.similarity_search(
    "B. Tech CSE semester subject names syllabus credits",
    k=20
)

for i, doc in enumerate(results):
    print(f"\n--- CHUNK {i+1} ---")
    print("SOURCE:", doc.metadata.get("source"))
    print(doc.page_content[:1200])