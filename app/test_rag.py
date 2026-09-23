from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os

load_dotenv()

# 1. Load embedding model
print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
   model_name="all-MiniLM-L6-v2"
)

# 2. Load existing Chroma database
print("Loading Chroma database...")

vectorstore = Chroma(
    persist_directory="chroma_db",
    embedding_function=embeddings
)

# 3. Ask a question
question = "When is Mid Sem Exam I?"

print("\nQuestion:", question)

# 4. Retrieve relevant chunks
results = vectorstore.similarity_search(
    question,
    k=3
)

print("\nRetrieved", len(results), "documents.")

# 5. Combine retrieved chunks
context = "\n\n".join(
    doc.page_content for doc in results
)

# 6. Load Groq LLM
print("\nLoading Groq...")

llm = llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b"
)

# 7. Give retrieved context + question to LLM
prompt = f"""
You are a helpful MITS college assistant.

Answer the question using ONLY the information provided
in the context below.

If the answer is not present in the context, say:
"I don't have that information in the college documents."

Context:
{context}

Question:
{question}

Answer:
"""

# 8. Generate answer
response = llm.invoke(prompt)

print("\n--- FINAL ANSWER ---")
print(response.content)