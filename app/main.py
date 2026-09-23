from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="MITS Chatbot")



# Load existing Chroma database


print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("Loading Chroma database...")

vectorstore = Chroma(
    persist_directory="../chroma_db",
    embedding_function=embeddings
)

print("Chroma database loaded successfully.")



# Load Groq LLM


print("Loading Groq...")

llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b"
)

print("Groq loaded successfully.")



# Request model


class Question(BaseModel):
    question: str



# Ask endpoint


@app.post("/ask")
def ask_question(q: Question):

    # Retrieve relevant chunks
    results = vectorstore.similarity_search(
        q.question,
        k=3
    )

    # Combine retrieved chunks
    context = "\n\n".join(
        doc.page_content for doc in results
    )

    # Create prompt
    prompt = f"""
You are a helpful MITS college assistant.

Answer the question using ONLY the information provided
in the context below.

If the answer is not present in the context, say:
"I don't have that information in the college documents."

Context:
{context}

Question:
{q.question}

Answer:
"""

    # Generate answer
    response = llm.invoke(prompt)

    return {
        "answer": response.content
    }



# Home page


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")



# Static files


app.mount(
    "/static",
    StaticFiles(directory="../static"),
    name="static"
)