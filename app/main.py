from pathlib import Path
import os

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import CrossEncoder

from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from syllabus_retriever import retrieve_syllabus

# =====================================================
# 1. PROJECT PATHS AND ENVIRONMENT
# =====================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

load_dotenv(BASE_DIR / ".env")

app = FastAPI(title="MITS Gwalior RAG Chatbot")
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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
# SYLLABUS QUESTION DETECTION AND RETRIEVAL
# =====================================================

def is_syllabus_query(question: str) -> bool:
    keywords = [
        "syllabus",
        "scheme of evaluation",
        "course structure"
    ]

    question_lower = question.lower()

    return any(keyword in question_lower for keyword in keywords)


def detect_semester(question: str):
    question_lower = question.lower()

    semester_map = {
        "1": 1, "i": 1,
        "2": 2, "ii": 2,
        "3": 3, "iii": 3,
        "4": 4, "iv": 4,
        "5": 5, "v": 5,
        "6": 6, "vi": 6,
        "7": 7, "vii": 7,
        "8": 8, "viii": 8
    }

    pattern = (
        r"\b(1|2|3|4|5|6|7|8|"
        r"VIII|VII|VI|V|IV|III|II|I)"
        r"(?:st|nd|rd|th)?\s*(?:semester|sem)\b"
        r"|\b(?:semester|sem)\s*"
        r"(VIII|VII|VI|V|IV|III|II|I|1|2|3|4|5|6|7|8)\b"
    )

    match = re.search(pattern, question_lower)

    if not match:
        return None

    semester_value = next(
        (group for group in match.groups() if group),
        None
    )

    return semester_map.get(semester_value.lower())


def answer_syllabus_question(question: str):

    department = detect_department(question)
    semester = detect_semester(question)

    if not department:
        return {
            "type": "syllabus",
            "answer": "Please specify the department: CSE or CSD.",
            "faculty": [],
            "sources": []
        }

    if not semester:
        return {
            "type": "syllabus",
            "answer": "Please specify the semester (1 to 8).",
            "faculty": [],
            "sources": []
        }

    syllabus_context = retrieve_syllabus(department, semester)

    if syllabus_context.startswith("No indexed syllabus"):
        return {
            "type": "syllabus",
            "answer": syllabus_context,
            "faculty": [],
            "sources": []
        }

    prompt = f"""
You are a helpful MITS Gwalior college assistant.

Answer the student's syllabus question using ONLY the
provided syllabus context.

Rules:
- Clearly list the subject names and subject codes.
- Include labs, projects and other listed courses.
- Do not invent or modify subject names or codes.
- Do not confuse marks, credits or contact hours with subjects.
- If a detail is missing, say it is not available in the context.

Syllabus context:
{syllabus_context}

Student question:
{question}

Answer:
"""

    response = llm.invoke(prompt)

    sources = []
    seen_sources = set()

    for line in syllabus_context.splitlines():
        if line.startswith("Source:"):
            source = line.replace("Source:", "", 1).strip()

        elif line.startswith("Page:"):
            page = line.replace("Page:", "", 1).strip()
            source_key = (source, page)

            if source_key not in seen_sources:
                seen_sources.add(source_key)
                sources.append({
                    "type": "pdf",
                    "source": source,
                    "page": page
                })

    return {
        "type": "syllabus",
        "answer": response.content,
        "faculty": [],
        "sources": sources
    }
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

    question_lower = question.lower()
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

    if not faculty:
        return []

    # Normalize question for name matching
    normalized_question = re.sub(
        r"[^a-z0-9\s]", " ", question_lower
    )
    normalized_question = " ".join(normalized_question.split())

    # STEP 1: Exact faculty-name matching gets priority
    exact_matches = []

    for doc in faculty:
        name = doc.metadata.get("faculty_name", "").lower()
        normalized_name = re.sub(r"[^a-z0-9\s]", " ", name)
        normalized_name = " ".join(normalized_name.split())

        if normalized_name and normalized_name in normalized_question:
            exact_matches.append(doc)

    if exact_matches:
        return exact_matches

    # STEP 2: Department-wide and all-faculty queries
    general_terms = [
        "show all",
        "all faculty",
        "list all",
        "faculty members",
        "show faculty",
        "list faculty",
        "cse faculty",
        "csd faculty",
        "faculty of cse",
        "faculty of csd"
    ]

    if any(term in normalized_question for term in general_terms):
        return faculty

    # STEP 3: Extract meaningful search terms
    stopwords = {
        "which", "who", "are", "the", "is", "in", "at",
        "of", "for", "and", "or", "do", "does", "has",
        "have", "with", "what", "work", "works", "working",
        "faculty", "members", "member", "teacher", "teachers",
        "professor", "professors", "from", "department",
        "specialization", "specializations", "interest",
        "interests", "area", "areas", "show", "me", "find",
        "tell", "about", "csd", "cse", "mits", "dr"
    }

    words = re.findall(r"[a-z]+", question_lower)

    search_terms = [
        word for word in words
        if word not in stopwords and len(word) > 1
    ]

    if not search_terms:
        return faculty

    # STEP 4: Normalize common academic terminology
    term_aliases = {
        "hod": "head",
        "specializations": "specialization",
        "interests": "interest"
    }

    search_terms = [
        term_aliases.get(term, term)
        for term in search_terms
    ]

    # STEP 5: Match relevant faculty fields
    matching_faculty = []

    for doc in faculty:
        metadata = doc.metadata

        searchable_fields = [
            str(metadata.get("faculty_name", "")),
            str(metadata.get("designation", "")),
            str(metadata.get("qualification", "")),
            str(metadata.get("area_of_interest", "")),
            str(metadata.get("email", ""))
        ]

        searchable_text = " ".join(searchable_fields).lower()

        matched_terms = sum(
            1 for term in search_terms
            if term in searchable_text
        )

        if matched_terms > 0:
            matching_faculty.append((matched_terms, doc))

    if not matching_faculty:
        return []

    # STEP 6: Return only the highest-scoring matches
    matching_faculty.sort(
        key=lambda item: item[0],
        reverse=True
    )

    best_score = matching_faculty[0][0]

    return [
        doc for score, doc in matching_faculty
        if score == best_score
    ]



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

        # Detect syllabus queries
    is_syllabus_query = any(
        word in question.lower()
        for word in [
            "syllabus",
            "scheme of evaluation",
            "course structure"
        ]
    )

    # Retrieve more chunks for syllabus queries
    retrieval_k = 20 if is_syllabus_query else 5

    ranked_lists = [
        vectorstore.similarity_search(
            query,
            k=retrieval_k
        )
        for query in queries
    ]

    # Combine results using RRF
    results = reciprocal_rank_fusion(ranked_lists)

    # Keep more candidates for syllabus queries
    candidates = deduplicate_documents(results)[
        :40 if is_syllabus_query else 15
    ]

    if is_syllabus_query:
        # Preserve more syllabus table chunks
        # instead of allowing the reranker to discard subject rows.
        final_results = candidates[:10]
    else:
        # Keep the existing reranking process for other queries
        final_results = rerank_documents(
            question,
            candidates,
            top_n=5
        )

    print("\nCandidates before reranking:", len(candidates))
    print("\nFinal chunks:", len(final_results))
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
    print("\n========== FINAL CONTEXT SENT TO LLM ==========")
    print(context)
    print("================================================")

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

        # Syllabus questions
    if is_syllabus_query(question):

        return answer_syllabus_question(question)

    # Faculty questions
    if is_faculty_query(question):

        return answer_faculty_question(question)

    # All other questions use normal RAG
    return answer_general_question(question)

# =====================================================
# 11. HEALTH CHECK
# =====================================================

@app.get("/")
def root():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health_check():

    return {
        "status": "healthy",
        "database": "connected",
        "models": "loaded"
    }
