from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
print("Loading PDFs...")

loader = PyPDFDirectoryLoader(".")

documents = loader.load()

print("Number of documents loaded:", len(documents))

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

chunks = splitter.split_documents(documents)

print("Number of chunks created:", len(chunks))

print("\n--- SAMPLE CHUNK ---")
print(chunks[0].page_content)

print("\nCreating embeddings...")

embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)


print("Embeddings model loaded.")
print("\nCreating Chroma database...")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="../chroma_db"
)

print("Chroma database created successfully.")