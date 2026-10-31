

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
    persist_directory="../chroma_db",
    embedding_function=embeddings
)

# 3. Load Groq
print("\nLoading Groq...")

llm = ChatGroq(
    api_key=os.environ.get("GROQ_API_KEY"),
    model_name="openai/gpt-oss-20b"
)

# 4. Ask a question
question = input("\nAsk MITS chatbot: ")

print("\nQuestion:", question)


# 5. Detect faculty-related questions
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


# 6. Faculty retrieval
if is_faculty_query:

    results = vectorstore.similarity_search(
        question,
        k=5,
        filter={"type": "faculty"}
    )

    print("\nRetrieved faculty records:", len(results))

    if not results:
        print("No faculty information found.")
        raise SystemExit

    # Remove duplicate faculty records, if any
    unique_faculty = {}

    for doc in results:
        name = doc.metadata.get("faculty_name", "")

        if name and name not in unique_faculty:
            unique_faculty[name] = doc

    faculty_docs = list(unique_faculty.values())

    context = "\n\n".join(
        doc.page_content for doc in faculty_docs
    )

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

    # Display photo and profile URLs for every retrieved faculty member
    print("\n--- FACULTY PHOTOS AND PROFILES ---")

    for doc in faculty_docs:
        metadata = doc.metadata

        print("\nFaculty:", metadata.get("faculty_name"))
        print("Photo:", metadata.get("photo_url", "Not available"))
        print("Profile:", metadata.get("profile_url", "Not available"))


# 7. Normal college-related query
else:

    results = vectorstore.similarity_search(
        question,
        k=3
    )

    print("\nRetrieved", len(results), "documents.")

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
