from pathlib import Path
import os

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

print("Loading embedding model...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

print("Loading Chroma database...")
vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings,
)

question = "When is Mid Sem Exam I?"
print("\nQuestion:", question)

results = vectorstore.similarity_search(question, k=3)
print("\nRetrieved", len(results), "documents.")

context = "\n\n".join(doc.page_content for doc in results)

print("\nLoading Groq...")
llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b",
)

prompt = f"""
You are a helpful MITS college assistant.

Answer the question using ONLY the information provided in the context below.
If the answer is not present in the context, say:
"I don't have that information in the college documents."

Context:
{context}

Question:
{question}

Answer:
"""

response = llm.invoke(prompt)
print("\n--- FINAL ANSWER ---")
print(response.content)