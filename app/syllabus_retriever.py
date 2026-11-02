
import re
from pathlib import Path
from collections import defaultdict

from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "chroma_db"

# Connect to existing ChromaDB
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)


# Semester names in Roman numerals
ROMAN_TO_SEMESTER = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8
}

SEMESTER_TO_ROMAN = {
    value: key for key, value in ROMAN_TO_SEMESTER.items()
}


def get_year_semesters(year):
    """Return the two semesters belonging to an academic year."""

    if year < 1 or year > 4:
        raise ValueError("Year must be between 1 and 4")

    first_semester = (year * 2) - 1

    return [first_semester, first_semester + 1]


def detect_semester(text):
    """Detect semester from scheme page headings."""

    pattern = (
        r"\b(VIII|VII|VI|V|IV|III|II|I)\s+Semester\b"
    )

    match = re.search(pattern, text, re.IGNORECASE)

    if not match:
        return None

    roman = match.group(1).upper()

    return ROMAN_TO_SEMESTER.get(roman)


def retrieve_syllabus(branch, semester):
    """
    Retrieve syllabus pages for one branch and semester.

    branch: CSE or CSD
    semester: integer from 1 to 8
    """

    branch = branch.upper().strip()

    if branch not in ["CSE", "CSD"]:
        return "Please specify CSE or CSD."

    if semester not in range(1, 9):
        return "Please specify a semester between 1 and 8."

    # Read existing indexed records
    data = vectorstore._collection.get(
        include=["documents", "metadatas"]
    )

    # Group chunks by source PDF and page
    pages = defaultdict(list)

    for content, metadata in zip(
        data["documents"],
        data["metadatas"]
    ):
        source = metadata.get("source", "")
        normalized_source = source.replace("\\", "/")
        path_parts = [
            part.upper() for part in normalized_source.split("/")
        ]

        # Only select the requested branch's scheme PDFs
        if branch not in path_parts:
            continue

        if "SCHEME" not in path_parts:
            continue

        if not normalized_source.lower().endswith(".pdf"):
            continue

        page = metadata.get("page", 0)

        pages[(normalized_source, page)].append(content)

    # Sort pages and identify which semester each page belongs to
    selected_pages = []

    for source in sorted(set(key[0] for key in pages)):
        source_pages = sorted(
            page for pdf, page in pages if pdf == source
        )

        current_semester = None

        for page in source_pages:
            chunks = pages[(source, page)]

            # Remove duplicate chunks while preserving order
            unique_chunks = list(dict.fromkeys(chunks))
            page_text = "\n".join(unique_chunks)

            detected = detect_semester(page_text)

            if detected is not None:
                current_semester = detected

            if (
                current_semester == semester
                and "scheme of evaluation" in page_text.lower()
                and "b. tech." in page_text.lower()
            ):
                selected_pages.append(
                    f"Source: {source}\nPage: {page}\n{page_text}"
                )

    if not selected_pages:
        return (
            f"No indexed syllabus found for {branch} "
            f"Semester {SEMESTER_TO_ROMAN[semester]}."
        )

    return "\n\n".join(selected_pages)


def retrieve_year_syllabus(branch, year):
    """Retrieve both semesters of the requested academic year."""

    semesters = get_year_semesters(year)

    results = []

    for semester in semesters:
        roman = SEMESTER_TO_ROMAN[semester]

        syllabus = retrieve_syllabus(branch, semester)

        results.append(
            f"\n{'=' * 60}\n"
            f"{branch.upper()} - SEMESTER {roman}\n"
            f"{'=' * 60}\n"
            f"{syllabus}"
        )

    return "\n".join(results)
