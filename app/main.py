from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="MITS Chatbot")


def generate_queries(question: str) -> list[str]:
    prompt = f"""
You generate search queries for a college information chatbot.

Generate exactly 3 alternative search queries for the user's question.

Rules:
- Preserve all years, dates, course names, and other specific details.
- Never introduce a year or date that the user did not mention.
- Keep each query focused on the same intent.
- Use different wording to improve document retrieval.
- Return only the 3 queries, one per line.
- Do not number them or add explanations.

User question: {question}
"""

    response = llm.invoke(prompt)
    

    queries = [
        line.strip().lstrip("0123456789.-) ")
        for line in response.content.splitlines()
        if line.strip()
    ]

    # Keep the original question and remove duplicates.
    all_queries = [question] + queries[:3]
    return list(dict.fromkeys(all_queries))

def reciprocal_rank_fusion(
    ranked_lists,
    k: int = 60
):
    scores = {}
    documents = {}

    for ranked_docs in ranked_lists:
        for rank, doc in enumerate(ranked_docs, start=1):
            # Use document text + metadata to identify a chunk.
            doc_id = (
                doc.page_content,
                tuple(sorted(doc.metadata.items()))
            )

            documents[doc_id] = doc

            scores[doc_id] = scores.get(doc_id, 0) + (
                1 / (k + rank)
            )

    ranked_ids = sorted(
        scores,
        key=scores.get,
        reverse=True
    )

    return [documents[doc_id] for doc_id in ranked_ids]



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

print("Loading reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

print("Reranker loaded successfully.")

# Request model


class Question(BaseModel):
    question: str



# Ask endpoint

def rerank_documents(question: str, documents, top_n: int = 5):
    if not documents:
        return []

    pairs = [
        (question, doc.page_content)
        for doc in documents
    ]

    scores = reranker.predict(pairs)

    
    ranked_docs = sorted(
        zip(documents, scores),
        key=lambda item: float(item[1]),
        reverse=True
    )

    print("\nReranker scores:")
    for doc, score in ranked_docs:
        print(f"{float(score):.4f} | {doc.page_content[:100]!r}")
    return [
        doc for doc, score in ranked_docs[:top_n]
    ]




@app.post("/ask")
def ask_question(q: Question):

    # 1. Generate alternative search queries
    queries = generate_queries(q.question)

    print("\nGenerated queries:")
    for query in queries:
        print("-", query)

    # 2. Retrieve chunks for each query
    ranked_lists = [
        vectorstore.similarity_search(query, k=5)
        for query in queries
    ]

    # 3. Combine rankings using RRF
    results = reciprocal_rank_fusion(ranked_lists)

    # 4. Keep up to 15 candidates
    candidates = results[:15]

    # 5. Rerank candidates against the original question
    results = rerank_documents(
        q.question,
        candidates,
        top_n=5
    )

    print("Candidates before reranking:", len(candidates))
    print("Final chunks after reranking:", len(results))

    # 6. Combine the final chunks into context
    context = "\n\n".join(
        doc.page_content for doc in results
    )

    # 7. Create a grounded prompt
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

    # 8. Generate the final answer
    response = llm.invoke(prompt)

    return {"answer": response.content}


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