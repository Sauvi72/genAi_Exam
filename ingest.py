import os
import shutil
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from dotenv import load_dotenv

load_dotenv()

def ingest_pdf():
    # Resolve path relative to this script or environment variable
    script_dir = Path(__file__).resolve().parent
    pdf_path = script_dir / os.getenv("PDF_PATH", "History_2024-25.pdf")
    chroma_dir = script_dir / os.getenv("CHROMA_DIR", "chroma_db")

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found at: {pdf_path}")

    print(f"Loading PDF from: {pdf_path}...")
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()
    total_pages = len(docs)
    print(f"Total pages loaded: {total_pages}")

    # Ensure 1-based page numbering in metadata and warn for empty pages
    empty_pages = []
    for idx, doc in enumerate(docs, start=1):
        # Enforce 1-based page index
        doc.metadata["page"] = idx
        doc.metadata["source"] = "History_2024-25.pdf"
        if not doc.page_content.strip():
            empty_pages.append(idx)

    if empty_pages:
        print(f"Warning: The following pages contain empty text: {empty_pages}")

    # Split text into chunks
    print("Splitting text into chunks (chunk_size=800, chunk_overlap=150)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        is_separator_regex=False
    )
    chunks = text_splitter.split_documents(docs)

    # Ensure each chunk preserves page and source metadata
    for chunk in chunks:
        if "page" not in chunk.metadata:
            chunk.metadata["page"] = 1
        chunk.metadata["source"] = "History_2024-25.pdf"

    total_chunks = len(chunks)
    print(f"Total chunks created: {total_chunks}")

    # Clean old Chroma directory if it exists
    if chroma_dir.exists():
        print(f"Removing existing Chroma database directory at {chroma_dir} for clean rerun...")
        shutil.rmtree(chroma_dir)

    # Initialize HuggingFace embeddings
    print("Initializing HuggingFace embeddings (sentence-transformers/all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Store in ChromaDB
    print(f"Storing chunks in ChromaDB at {chroma_dir} with collection 'history_catalogue'...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="history_catalogue",
        persist_directory=str(chroma_dir)
    )

    print("--- Ingestion Summary ---")
    print(f"Total pages: {total_pages}")
    print(f"Total chunks: {total_chunks}")
    print("Ingestion complete")

if __name__ == "__main__":
    ingest_pdf()
