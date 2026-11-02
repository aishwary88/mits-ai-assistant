


import json
import re
import hashlib
from pathlib import Path
import time
import requests

from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from urllib.robotparser import RobotFileParser

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
FACULTY_DIR = BASE_DIR / "faculty-data"
DATA_DIR = BASE_DIR / "Mits-Data"
DB_DIR = BASE_DIR / "chroma_db"


# Normalize PDF source paths so old and new records can be compared
def normalize_source(source):
    source = str(source).replace("\\", "/")

    marker = "Mits-Data/"
    position = source.lower().find(marker.lower())

    if position != -1:
        source = source[position + len(marker):]

    return source.lstrip("./")


# Generate a stable ID for each PDF chunk
def generate_pdf_id(source, page, content):
    unique_text = f"{source}|{page}|{content}"
    return "pdf_" + hashlib.sha1(
        unique_text.encode("utf-8")
    ).hexdigest()


# 1. Load PDF documents
def load_pdf_data():

    print("Loading PDFs...")

    loader = PyPDFDirectoryLoader(
        str(DATA_DIR),
        glob="**/*.pdf"
    )

    documents = loader.load()

    print("PDF documents loaded:", len(documents))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    chunks = splitter.split_documents(documents)

    for chunk in chunks:
        chunk.metadata["source"] = normalize_source(
            chunk.metadata.get("source", "")
        )
        chunk.metadata["type"] = "pdf"

    print("PDF chunks created:", len(chunks))

    return chunks


# 2. Load faculty JSON files
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
# 3. Website ingestion

BASE_URL = "https://web.mitsgwalior.in"

WEBSITE_SEEDS = [
    BASE_URL + "/",
    BASE_URL + "/academic",
    BASE_URL + "/latest-notices",
    BASE_URL + "/latest-admission",
    BASE_URL + "/admission/ug-admissions",
    BASE_URL + "/about-institute/about-mits",
    BASE_URL + "/about-institute/vision-mission",
    BASE_URL + "/all-faculty/faculty-list",
    BASE_URL + "/faculty-profiles-cse-2",
    BASE_URL + "/contacts-cse",
    BASE_URL + "/faculty-profiles-cai",
    BASE_URL + "/contact-us",
]

MAX_WEBSITE_PAGES = 80

HEADERS = {
    "User-Agent": "MITS-RAG-Research-Bot/1.0"
}


def normalize_url(url):
    url, _ = urldefrag(url)
    parsed = urlparse(url)

    # Remove query strings and fragments
    clean_url = parsed._replace(
        query="",
        fragment=""
    ).geturl()

    return clean_url.rstrip("/")


def is_valid_website_url(url):

    parsed = urlparse(url)

    if parsed.netloc.lower() != "web.mitsgwalior.in":
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    # Ignore URLs with query parameters
    if parsed.query:
        return False

    ignored_extensions = (
        ".pdf", ".jpg", ".jpeg", ".png", ".gif",
        ".webp", ".svg", ".zip", ".doc", ".docx",
        ".xls", ".xlsx", ".mp4", ".mp3"
    )

    if parsed.path.lower().endswith(ignored_extensions):
        return False

    ignored_paths = (
        "/administrator",
        "/login",
        "/component/users",
    )

    if any(path in parsed.path.lower() for path in ignored_paths):
        return False

    return True


def get_robots_parser():

    robots_url = BASE_URL + "/robots.txt"

    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = requests.get(
            robots_url,
            headers=HEADERS,
            timeout=10
        )

        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            return parser

    except requests.RequestException as error:
        print("Could not read robots.txt:", error)

    return None


def extract_page_content(url, robots_parser):

    if robots_parser and not robots_parser.can_fetch(
        HEADERS["User-Agent"], url
    ):
        print("Blocked by robots.txt:", url)
        return None, None, []

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if "text/html" not in content_type:
            return None, None, []

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        title = (
            soup.title.get_text(" ", strip=True)
            if soup.title else url
        )

        # Collect internal links before removing navigation
        links = []

        for anchor in soup.find_all("a", href=True):

            link = urljoin(url, anchor["href"])
            link = normalize_url(link)

            if is_valid_website_url(link):
                links.append(link)

        # Remove irrelevant page elements
        for element in soup([
            "script", "style", "noscript",
            "nav", "footer", "header",
            "aside", "form"
        ]):
            element.decompose()

        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.body
            or soup
        )

        text_content = main_content.get_text(
            separator="\n",
            strip=True
        )

        # Remove excessive blank lines
        text_content = re.sub(
            r"\n{3,}",
            "\n\n",
            text_content
        )

        if len(text_content) < 100:
            return None, None, links

        return title, text_content, links

    except requests.RequestException as error:

        print("Website page failed:", url, error)
        return None, None, []


def load_website_data():

    print("\nStarting MITS website crawling...")

    robots_parser = get_robots_parser()

    visited = set()
    queue = list(WEBSITE_SEEDS)

    website_pages = []

    while queue and len(visited) < MAX_WEBSITE_PAGES:

        url = normalize_url(queue.pop(0))

        if url in visited:
            continue

        if not is_valid_website_url(url):
            continue

        visited.add(url)

        print(
            f"Crawling {len(visited)}/{MAX_WEBSITE_PAGES}:",
            url
        )

        title, content, links = extract_page_content(
            url,
            robots_parser
        )

        if content:

            website_pages.append({
                "url": url,
                "title": title,
                "content": content
            })

        for link in links:

            if (
                link not in visited
                and link not in queue
                and len(visited) + len(queue) < MAX_WEBSITE_PAGES
            ):
                queue.append(link)

        # Avoid sending requests too quickly
        time.sleep(0.3)

    print("Website pages successfully extracted:", len(website_pages))

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    website_documents = []

    for page in website_pages:

        document = Document(
            page_content=page["content"],
            metadata={
                "source": page["url"],
                "title": page["title"],
                "type": "website"
            }
        )

        chunks = splitter.split_documents([document])

        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_index"] = index
            website_documents.append(chunk)

    print("Website chunks created:", len(website_documents))

    return website_documents


def generate_website_id(source, index, content):

    unique_text = f"{source}|{index}|{content}"

    return "website_" + hashlib.sha1(
        unique_text.encode("utf-8")
    ).hexdigest()


def save_website_data(vectorstore, website_docs):

    print("\nUpdating website records in ChromaDB...")

    # Get existing website records only
    existing = vectorstore._collection.get(
        where={"type": "website"},
        include=["metadatas"]
    )

    existing_by_source = {}

    for record_id, metadata in zip(
        existing["ids"],
        existing["metadatas"]
    ):

        source = metadata.get("source", "")

        existing_by_source.setdefault(
            source, set()
        ).add(record_id)

    new_documents = []
    new_ids = []

    # Group new chunks by their source URL
    new_by_source = {}

    for doc in website_docs:

        source = doc.metadata["source"]
        index = doc.metadata["chunk_index"]

        record_id = generate_website_id(
            source,
            index,
            doc.page_content
        )

        new_by_source.setdefault(
            source, set()
        ).add(record_id)

        # Existing identical chunks do not need re-embedding
        if record_id not in existing_by_source.get(
            source, set()
        ):

            new_documents.append(doc)
            new_ids.append(record_id)

    # Delete obsolete chunks only for pages crawled successfully
    ids_to_delete = []

    for source, old_ids in existing_by_source.items():

        if source not in new_by_source:
            continue

        obsolete_ids = old_ids - new_by_source[source]
        ids_to_delete.extend(obsolete_ids)

    if ids_to_delete:
        vectorstore._collection.delete(
            ids=ids_to_delete
        )

    if new_documents:

        vectorstore.add_documents(
            documents=new_documents,
            ids=new_ids
        )

    print("New website chunks added:", len(new_documents))
    print("Obsolete website chunks removed:", len(ids_to_delete))
    print("Website ingestion completed!")


# 3. Load all data
print("\nLoading PDF data...")
pdf_docs = load_pdf_data()

print("\nLoading faculty data...")
faculty_docs = load_faculty_data()

print("Faculty records loaded:", len(faculty_docs))
print("\nLoading MITS website data...")
website_docs = load_website_data()

print("Website records loaded:", len(website_docs))


# 4. Load embedding model
print("\nLoading embedding model...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)


# 5. Connect to existing ChromaDB
print("\nConnecting to existing ChromaDB...")

vectorstore = Chroma(
    persist_directory=str(DB_DIR),
    embedding_function=embeddings
)


# 6. Find existing PDF chunks to prevent duplicates
print("\nChecking existing PDF records...")

existing = vectorstore._collection.get(
    include=["documents", "metadatas"]
)

existing_pdf_signatures = set()

for content, metadata in zip(
    existing["documents"],
    existing["metadatas"]
):
    source = metadata.get("source", "")

    if source.lower().endswith(".pdf"):
        source = normalize_source(source)
        page = metadata.get("page", 0)

        signature = (source, page, content)
        existing_pdf_signatures.add(signature)


# 7. Add only new PDF chunks
new_pdf_docs = []
new_pdf_ids = []

for doc in pdf_docs:

    source = doc.metadata["source"]
    page = doc.metadata.get("page", 0)

    signature = (source, page, doc.page_content)

    if signature not in existing_pdf_signatures:

        new_pdf_docs.append(doc)
        new_pdf_ids.append(
            generate_pdf_id(source, page, doc.page_content)
        )

        existing_pdf_signatures.add(signature)


if new_pdf_docs:

    vectorstore.add_documents(
        documents=new_pdf_docs,
        ids=new_pdf_ids
    )

print("New PDF chunks added:", len(new_pdf_docs))


# 8. Add or update faculty records using stable IDs
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


if faculty_docs:

    vectorstore.add_documents(
        documents=faculty_docs,
        ids=faculty_ids
    )

    print("Faculty records added/updated:", len(faculty_docs))
if faculty_docs:

    vectorstore.add_documents(
        documents=faculty_docs,
        ids=faculty_ids
    )

    print("Faculty records added/updated:", len(faculty_docs))
    # 10. Add/update website records
save_website_data(vectorstore, website_docs)

# 9. Verify database
print("\nTotal records in ChromaDB:",
      vectorstore._collection.count())

print("PDF ingestion completed!")
print("Faculty ingestion completed!")
print("All ingestion completed successfully!")
