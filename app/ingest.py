

import json
import re
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
FACULTY_DIR = BASE_DIR / "faculty-data"
DB_DIR = BASE_DIR / "chroma_db"


# 1. Load faculty JSON files
def load_faculty_data():

    faculty_documents = []

    files = {
        "CSE": FACULTY_DIR / "cse_faculty.json",
        "CSD": FACULTY_DIR / "csd_faculty.json"
    }

    for department, file_path in files.items():

        with open(file_path, "r", encoding="utf-8") as f:
            faculty_list = json.load(f)

        for faculty in faculty_list:

            interests = faculty.get("area_of_interest") or []
            emails = faculty.get("email") or []

            if isinstance(emails, str):
                emails = [emails]

            if isinstance(interests, str):
                interests = [interests]

            content = f"""
            Faculty Name: {faculty.get('name', 'Not available')}
            Department: {faculty.get('department', department)}
            Designation: {faculty.get('designation', 'Not available')}
            Qualification: {faculty.get('qualification', 'Not available')}
            Areas of Interest: {', '.join(interests)}
            Email: {', '.join(emails)}
            Phone: {faculty.get('phone') or 'Not available'}
            """

            metadata = {
                "type": "faculty",
                "department": department,
                "faculty_name": faculty.get("name", "Unknown"),
                "designation": faculty.get("designation") or "",
                "qualification": faculty.get("qualification") or "",
                "area_of_interest": ", ".join(interests),
                "email": ", ".join(emails),
                "phone": faculty.get("phone") or "",
                "source": file_path.name
            }

            # Include photo URL when available
            if faculty.get("photo_url"):
                metadata["photo_url"] = faculty["photo_url"]

            if faculty.get("profile_url"):
                metadata["profile_url"] = faculty["profile_url"]

            faculty_documents.append(
                Document(
                    page_content=content,
                    metadata=metadata
                )
            )

    return faculty_documents


# 2. Load faculty records
print("Loading faculty data...")

faculty_docs = load_faculty_data()

print("Faculty records loaded:", len(faculty_docs))


# 3. Load embedding model
print("Loading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)


# 4. Connect to existing ChromaDB
print("Connecting to existing ChromaDB...")

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)


# 5. Generate stable IDs
faculty_ids = []

for faculty in faculty_docs:

    name = faculty.metadata["faculty_name"]
    department = faculty.metadata["department"]

    slug = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        name.lower()
    ).strip("_")

    faculty_ids.append(f"faculty_{department}_{slug}")


# 6. Add or update faculty records
if faculty_docs:

    vectorstore.add_documents(
        documents=faculty_docs,
        ids=faculty_ids
    )

    print("Faculty records added/updated successfully!")

else:
    print("No faculty records found!")


# 7. Verify database
print("Total records in ChromaDB:",
      vectorstore._collection.count())

print("Faculty ingestion completed!")
