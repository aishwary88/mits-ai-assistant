
import json
import re
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

BASE_DIR = Path(__file__).resolve().parent.parent
FACULTY_DIR = BASE_DIR / "faculty-data"
DB_DIR = BASE_DIR / "chroma_db"

# Load both faculty JSON files
faculty_docs = []
faculty_ids = []

for department in ["CSE", "CSD"]:
    file_path = FACULTY_DIR / f"{department.lower()}_faculty.json"

    with open(file_path, "r", encoding="utf-8") as f:
        faculty_list = json.load(f)

    for faculty in faculty_list:
        interests = faculty.get("area_of_interest") or []
        emails = faculty.get("email") or []

        if isinstance(interests, str):
            interests = [interests]
        if isinstance(emails, str):
            emails = [emails]

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

        for field in ["photo_url", "profile_url"]:
            if faculty.get(field):
                metadata[field] = faculty[field]

        faculty_docs.append(
            Document(page_content=content, metadata=metadata)
        )

        slug = re.sub(
            r"[^a-zA-Z0-9]+", "_", faculty["name"].lower()
        ).strip("_")

        faculty_ids.append(f"faculty_{department}_{slug}")

# Connect to existing ChromaDB
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)

# Update faculty records only
vectorstore.add_documents(
    documents=faculty_docs,
    ids=faculty_ids
)

# Verify
records = vectorstore._collection.get(
    where={"type": "faculty"},
    include=["metadatas"]
)

with_photos = sum(
    1 for m in records["metadatas"] if m.get("photo_url")
)
with_profiles = sum(
    1 for m in records["metadatas"] if m.get("profile_url")
)

print("\nFaculty update completed!")
print("Faculty records in database:", len(records["ids"]))
print("Records with photos:", with_photos)
print("Records with profile URLs:", with_profiles)
print("Total ChromaDB records:", vectorstore._collection.count())
