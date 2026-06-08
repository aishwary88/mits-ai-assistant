from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import RetrievalQA
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="MITS Chatbot")

# Load and index documents
def load_documents():
    documents = []
    
    # Load text files
    if os.path.exists("data"):
        for file in os.listdir("data"):
            filepath = os.path.join("data", file)
            if file.endswith(".txt"):
                loader = TextLoader(filepath, encoding="utf-8")
                documents.extend(loader.load())
            elif file.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
                documents.extend(loader.load())
    
    return documents

def setup_qa_chain():
    documents = load_documents()
    
    if not documents:
        return None
    
    # Split documents
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    
    # Embeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )
    
    # Vector store
    vectorstore = Chroma.from_documents(chunks, embeddings)
    
    # LLM
    llm = ChatGroq(
        api_key=os.environ.get("GROQ_API_KEY"),
        model_name="llama3-8b-8192"
    )
    
    # QA Chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 3})
    )
    
    return qa_chain

qa_chain = setup_qa_chain()

class Question(BaseModel):
    question: str

@app.post("/ask")
def ask_question(q: Question):
    if not qa_chain:
        return {"answer": "No data loaded. Please add files to the data folder."}
    
    result = qa_chain.invoke({"query": q.question})
    return {"answer": result["result"]}

@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")

app.mount("/static", StaticFiles(directory="static"), name="static")