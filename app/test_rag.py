


from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from dotenv import load_dotenv
import os


# 1. Set project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

load_dotenv(BASE_DIR / ".env")


# 2. Load embedding model
print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)


# 3. Load existing Chroma database
print("Loading Chroma database...")

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)


# 4. Load Groq
print("\nLoading Groq...")

llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b"
)


# 5. Ask a question
question = input("\nAsk MITS chatbot: ")

print("\nQuestion:", question)


# 6. Detect faculty-related questions
faculty_keywords = [
    "faculty",
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

is_faculty_query = any(
    keyword in question.lower()
    for keyword in faculty_keywords
)


# 7. Faculty retrieval
if is_faculty_query:

    department = None

    question_lower = question.lower()

    if (
        "csd" in question_lower
        or "computer science and design" in question_lower
    ):
        department = "CSD"

    elif (
        "cse" in question_lower
        or "computer science and engineering" in question_lower
    ):
        department = "CSE"

    # Build ChromaDB metadata filter
    if department:
        metadata_filter = {
            "$and": [
                {"type": "faculty"},
                {"department": department}
            ]
        }
    else:
        metadata_filter = {
            "type": "faculty"
        }

    results = vectorstore.similarity_search(
        question,
        k=10,
        filter=metadata_filter
    )

    print("\nRetrieved faculty records:", len(results))

    if not results:
        print("No faculty information found.")
        raise SystemExit

    # Remove duplicate faculty records
    unique_faculty = {}

    for doc in results:
        name = doc.metadata.get("faculty_name", "")

        if name and name not in unique_faculty:
            unique_faculty[name] = doc

    faculty_docs = list(unique_faculty.values())

    # Prepare faculty context
    context = "\n\n".join(
        doc.page_content for doc in faculty_docs
    )

    # Generate faculty answer
    prompt = f"""
    You are a helpful MITS Gwalior college assistant.

    Answer using ONLY the faculty information below.

    Do not invent information.
    For specialization questions, mention the faculty members
    whose areas of interest match the question.

    Faculty information:
    {context}

    Student question:
    {question}

    Give a clear and structured answer.
    """

    response = llm.invoke(prompt)

    print("\n--- FACULTY INFORMATION ---")
    print(response.content)

    # Display faculty photos and profiles
    print("\n--- FACULTY PHOTOS AND PROFILES ---")

    for doc in faculty_docs:
        metadata = doc.metadata

        print("\nFaculty:", metadata.get("faculty_name"))
        print("Department:", metadata.get("department"))
        print("Photo:", metadata.get("photo_url") or "Not available")
        print("Profile:", metadata.get("profile_url") or "Not available")


# 8. Normal college-related query
else:

    results = vectorstore.similarity_search(
        question,
        k=3
    )

    print("\nRetrieved", len(results), "documents.")

    if not results:
        print("No relevant college information found.")
        raise SystemExit

    context = "\n\n".join(
        doc.page_content for doc in results
    )

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

    response = llm.invoke(prompt)

    print("\n--- FINAL ANSWER ---")
    print(response.content)