from pathlib import Path

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Mits-Data"
DB_DIR = BASE_DIR / "chroma_db"

print("Loading PDFs from MITS data folder...")
loader = PyPDFDirectoryLoader(str(DATA_DIR), glob="**/*.pdf")
documents = loader.load()

print("Number of documents loaded:", len(documents))

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(documents)

print("Number of chunks created:", len(chunks))

if not chunks:
    raise RuntimeError(f"No PDF chunks were created from {DATA_DIR}.")

print("\n--- SAMPLE CHUNK ---")
print(chunks[0].page_content)

print("\nCreating embeddings...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

print("Embeddings model loaded.")
print("\nCreating Chroma database...")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory=str(DB_DIR),
)

print("Chroma database created successfully at:", DB_DIR)