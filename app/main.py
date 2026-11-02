
from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# =====================================================
# 1. PROJECT PATHS AND ENVIRONMENT
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="MITS Gwalior RAG Chatbot")


# =====================================================
# 2. LOAD MODELS AND VECTOR DATABASE
# =====================================================

print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

print("Loading Chroma database...")

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)

print("Chroma database loaded successfully.")


print("Loading Groq...")

api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    raise RuntimeError("GROQ_API_KEY not found in project .env file.")

llm = ChatGroq(
    api_key=api_key,
    model_name="openai/gpt-oss-20b"
)

print("Groq loaded successfully.")


print("Loading CrossEncoder reranker...")

reranker = CrossEncoder(
    "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

print("Reranker loaded successfully.")


# =====================================================
# 3. REQUEST MODEL
# =====================================================

class Question(BaseModel):
    question: str


# =====================================================
# 4. FACULTY QUESTION DETECTION
# =====================================================

FACULTY_KEYWORDS = [
    "faculty",
    "faculty members",
    "professor",
    "teacher",
    "teaches",
    "teaching",
    "hod",
    "dean",
    "specialization",
    "specialisation",
    "qualification",
    "who is",
    "who are",
    "tell me about",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "data mining",
    "sentiment analysis",
    "image processing",
    "natural language processing",
    "nlp"
]


def is_faculty_query(question: str) -> bool:

    question_lower = question.lower()

    return any(
        keyword in question_lower
        for keyword in FACULTY_KEYWORDS
    )


def detect_department(question: str):

    question_lower = question.lower()

    if (
        "csd" in question_lower
        or "computer science and design" in question_lower
    ):
        return "CSD"

    if (
        "cse" in question_lower
        or "computer science and engineering" in question_lower
    ):
        return "CSE"

    return None


# =====================================================
# 5. MULTI-QUERY GENERATION
# =====================================================

def generate_queries(question: str) -> list[str]:

    prompt = f"""
You generate search queries for a college information chatbot.

Generate exactly 3 alternative search queries for the user's question.

Rules:
- Preserve all years, dates, course names, and specific details.
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

    all_queries = [question] + queries[:3]

    return list(dict.fromkeys(all_queries))


# =====================================================
# 6. RECIPROCAL RANK FUSION
# =====================================================

def freeze_metadata(value):

    if isinstance(value, dict):
        return tuple(
            sorted(
                (key, freeze_metadata(val))
                for key, val in value.items()
            )
        )

    if isinstance(value, (list, tuple)):
        return tuple(freeze_metadata(item) for item in value)

    return value


def reciprocal_rank_fusion(ranked_lists, k: int = 60):

    scores = {}
    documents = {}

    for ranked_docs in ranked_lists:

        for rank, doc in enumerate(ranked_docs, start=1):

            doc_id = (
                doc.page_content,
                freeze_metadata(doc.metadata)
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

    return [
        documents[doc_id]
        for doc_id in ranked_ids
    ]


# =====================================================
# 7. CROSSENCODER RERANKING
# =====================================================

def rerank_documents(
    question: str,
    documents,
    top_n: int = 5
):

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
        print(
            f"{float(score):.4f} | "
            f"{doc.page_content[:100]!r}"
        )

    return [
        doc
        for doc, score in ranked_docs[:top_n]
    ]


# =====================================================
# 8. FACULTY RETRIEVAL
# =====================================================


import re

def retrieve_faculty(question: str):

    department = detect_department(question)

    # Retrieve faculty records from the selected department
    if department:
        metadata_filter = {
            "$and": [
                {"type": "faculty"},
                {"department": department}
            ]
        }
    else:
        metadata_filter = {"type": "faculty"}

    results = vectorstore.similarity_search(
        question,
        k=30,
        filter=metadata_filter
    )

    # Remove duplicate faculty records
    unique_faculty = {}

    for doc in results:
        name = doc.metadata.get("faculty_name", "")

        if name and name not in unique_faculty:
            unique_faculty[name] = doc

    faculty = list(unique_faculty.values())

    # Return all faculty for general listing questions
    general_terms = [
        "show all", "all faculty", "list all",
        "faculty members", "show faculty",
        "list faculty"
    ]

    if any(term in question.lower() for term in general_terms):
        return faculty

    # Extract meaningful search terms
    stopwords = {
        "which", "who", "are", "the", "is", "in", "at",
        "of", "for", "and", "or", "do", "does", "has",
        "have", "with", "what", "work", "works", "working",
        "faculty", "members", "member", "teacher", "teachers",
        "professor", "professors", "from", "department",
        "specialization", "specializations", "interest",
        "interests", "area", "areas", "show", "me", "find",
        "tell", "about", "csd", "cse"
    }

    words = re.findall(r"[a-z]+", question.lower())

    search_terms = [
        word for word in words
        if word not in stopwords and len(word) > 1
    ]

    # Filter faculty using their areas of interest
    if not search_terms:
        return faculty

    matching_faculty = []

    for doc in faculty:
        interests = doc.metadata.get(
            "area_of_interest", ""
        ).lower()

        if all(term in interests for term in search_terms):
            matching_faculty.append(doc)

    return matching_faculty



def answer_faculty_question(question: str):

    faculty_docs = retrieve_faculty(question)

    print("\nRetrieved faculty records:", len(faculty_docs))

    if not faculty_docs:
        return {
            "type": "faculty",
            "answer": "I couldn't find matching faculty information in the college database.",
            "faculty": [],
            "sources": []
        }

    faculty_data = []

    for doc in faculty_docs:
        metadata = doc.metadata

        faculty_data.append({
            "name": metadata.get("faculty_name"),
            "department": metadata.get("department"),
            "designation": metadata.get("designation"),
            "qualification": metadata.get("qualification"),
            "area_of_interest": metadata.get("area_of_interest"),
            "email": metadata.get("email"),
            "phone": metadata.get("phone"),
            "photo_url": metadata.get("photo_url"),
            "profile_url": metadata.get("profile_url")
        })

    # Build answer directly from retrieved structured data
    answer_lines = [
        "## MITS Faculty Information",
        ""
    ]

    for faculty in faculty_data:

        answer_lines.append(f"### {faculty['name']}")
        answer_lines.append(f"- Department: {faculty['department']}")
        answer_lines.append(f"- Designation: {faculty['designation']}")
        answer_lines.append(f"- Qualification: {faculty['qualification']}")
        answer_lines.append(f"- Areas of Interest: {faculty['area_of_interest']}")

        if faculty["photo_url"]:
            answer_lines.append(
                f"![{faculty['name']}]({faculty['photo_url']})"
            )

        if faculty["profile_url"]:
            answer_lines.append(
               f"[View Official Profile]({faculty['profile_url']})"
            )

        answer_lines.append("")

    sources = [
        {
            "type": "faculty",
            "name": doc.metadata.get("faculty_name"),
            "department": doc.metadata.get("department")
        }
        for doc in faculty_docs
    ]

    return {
        "type": "faculty",
        "answer": "\n".join(answer_lines),
        "faculty": faculty_data,
        "sources": sources
    }



# =====================================================
# 9. NORMAL DOCUMENT RETRIEVAL
# =====================================================

def deduplicate_documents(documents):

    unique_docs = []
    seen = set()

    for doc in documents:

        # Normalize content to detect duplicate chunks
        content_key = " ".join(doc.page_content.lower().split())

        if content_key not in seen:
            seen.add(content_key)
            unique_docs.append(doc)

    return unique_docs

def answer_general_question(question: str):

    # Generate alternative queries
    queries = generate_queries(question)

    print("\nGenerated queries:")

    for query in queries:
        print("-", query)

    # Retrieve chunks for every query
    ranked_lists = [
        vectorstore.similarity_search(
            query,
            k=5
        )
        for query in queries
    ]

    # Combine results using RRF
    results = reciprocal_rank_fusion(ranked_lists)

    # Keep top 15 candidates
    candidates = deduplicate_documents(results)[:15]

    # Rerank candidates using CrossEncoder
    final_results = rerank_documents(
        question,
        candidates,
        top_n=5
    )

    print("\nCandidates before reranking:", len(candidates))
    print("Final chunks after reranking:", len(final_results))

    if not final_results:

        return {
            "type": "general",
            "answer": "I don't have that information in the college documents.",
            "faculty": [],
            "sources": []
        }

    context = "\n\n".join(
        doc.page_content
        for doc in final_results
    )

    prompt = f"""
You are a helpful MITS Gwalior college assistant.

Answer the question using ONLY the information provided
in the context below.

If the answer is not present in the context, say:
"I don't have that information in the college documents."

Do not invent facts, dates, fees, or other details.

Context:
{context}

Question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    # Return source information with the answer
    
    # Return unique source information
    sources = []
    seen_sources = set()

    for doc in final_results:

        metadata = doc.metadata

        source_key = (
            metadata.get("type", "pdf"),
            metadata.get("source"),
            metadata.get("page")
        )

        if source_key not in seen_sources:
            seen_sources.add(source_key)

            sources.append({
                "type": metadata.get("type", "pdf"),
                "source": metadata.get("source"),
                "page": metadata.get("page")
            })

    return {
        "type": "general",
        "answer": response.content,
        "faculty": [],
        "sources": sources
    }



# =====================================================
# 10. MAIN CHAT ENDPOINT
# =====================================================

@app.post("/ask")
@app.post("/chat")
@app.post("/api/chat")
def ask_question(q: Question):

    question = q.question.strip()

    if not question:
        return {
            "type": "error",
            "answer": "Please enter a question.",
            "faculty": [],
            "sources": []
        }

    print("\n===================================")
    print("Student question:", question)
    print("===================================")

    if is_faculty_query(question):

        return answer_faculty_question(question)

    return answer_general_question(question)


# =====================================================
# 11. HEALTH CHECK
# =====================================================

@app.get("/")
def root():

    return {
        "message": "MITS Gwalior RAG Chatbot Backend is running.",
        "status": "active",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "database": "connected",
        "models": "loaded"
    }
