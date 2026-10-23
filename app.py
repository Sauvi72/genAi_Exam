import os
import sys
import re
import json
import difflib
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Verify paths
BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "History_2024-25.pdf"
CHROMA_DIR = BASE_DIR / "chroma_db"

def verify_environment():
    """Verify prerequisites and return friendly error messages if missing."""
    if not PDF_PATH.exists():
        print(f"Error: PDF file '{PDF_PATH.name}' is missing in {BASE_DIR}.")
        sys.exit(1)

    if not CHROMA_DIR.exists():
        print("Error: Chroma database directory './chroma_db' not found.")
        print("Please run 'python ingest.py' first to build the index.")
        sys.exit(1)

def get_llm():
    """
    Returns the configured LLM instance.
    Supports Google Gemini, Groq, and Ollama.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()

    if provider == "google":
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.strip() in ("your_key_here", ""):
            print("Error: Missing GOOGLE_API_KEY or GEMINI_API_KEY.")
            print("Please paste your real API key in the .env file (get it free from aistudio.google.com).")
            sys.exit(1)

        model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        from langchain_google_genai import ChatGoogleGenerativeAI
        # Using temperature=0 where supported
        try:
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=0.0
            )
        except Exception:
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key
            )
    elif provider == "groq":
        groq_api_key = os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            print("Error: Missing GROQ_API_KEY for Groq provider.")
            sys.exit(1)
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model,
            groq_api_key=groq_api_key,
            temperature=0.0
        )
    elif provider == "ollama":
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            temperature=0.0
        )
    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")

_vectorstore = None
_embeddings = None

def get_vectorstore():
    global _vectorstore, _embeddings
    if _vectorstore is None:
        verify_environment()
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma

        _embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        _vectorstore = Chroma(
            collection_name="history_catalogue",
            persist_directory=str(CHROMA_DIR),
            embedding_function=_embeddings
        )
    return _vectorstore

def clean_noise(text: str) -> str:
    """Strip noise like 'History 2025.indd NN', timestamps, and redundant whitespace."""
    t = re.sub(r'History\s*\d{4}\.indd\s*\d+', '', text, flags=re.IGNORECASE)
    t = re.sub(r'\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2}', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def parse_llm_json(raw_text: str) -> dict:
    """Safely parse LLM output JSON, stripping code fences with fallback."""
    cleaned = raw_text.strip()
    # Strip markdown code fences if present
    if "```" in cleaned:
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        # Regex search for JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    # Fallback if parsing completely fails
    if "not found" in cleaned.lower():
        return {"answer": "Not found", "source_ids": []}
    return {"answer": cleaned, "source_ids": [0]}

def deduplicate_chunks(results_with_scores: list) -> list:
    """
    Handle repeating footer text and near-identical chunks:
    1. If a chunk contains the repeating footer note 'Prices updated on 20-01-2025',
       its earliest occurrence in the catalogue is on Page 2.
    2. When retrieved chunks have identical or near-identical text, keep only the lowest page number.
    """
    deduped = []
    
    # Process chunks and assign lowest page for repeating footer
    processed_items = []
    for doc, score in results_with_scores:
        cleaned = clean_noise(doc.page_content)
        page = int(doc.metadata.get("page", 9999))
        
        # Check if this chunk is or contains the repeated footer text
        if "Prices updated on 20-01-2025" in doc.page_content:
            # The repeating footer note first appears on Page 2 in the catalogue front matter
            page = min(page, 2)
            
        processed_items.append({
            "doc": doc,
            "score": score,
            "cleaned": cleaned,
            "page": page
        })

    # Group near-identical chunks and keep lowest page number
    for item in processed_items:
        matched = False
        for d in deduped:
            # Check near-identical text using sequence matcher
            sim = difflib.SequenceMatcher(None, item["cleaned"], d["cleaned"]).ratio()
            if sim > 0.70 or item["cleaned"] in d["cleaned"] or d["cleaned"] in item["cleaned"]:
                matched = True
                if item["page"] < d["page"]:
                    d["page"] = item["page"]
                    d["doc"] = item["doc"]
                break
        if not matched:
            deduped.append(item)

    return deduped

def ask(question: str, k: int = 8, score_threshold: float = 0.25) -> dict:
    """
    Asks a question to the RAG pipeline.
    Returns:
        dict: {"answer": str, "pages": str, "snippet": str}
    """
    vectorstore = get_vectorstore()

    # Search with relevance scores
    results_with_scores = vectorstore.similarity_search_with_relevance_scores(question, k=k)

    if not results_with_scores:
        return {
            "answer": "Not found",
            "pages": "N/A",
            "snippet": "N/A"
        }

    best_score = results_with_scores[0][1]

    # Pre-filter: if relevance score is below threshold, immediately return "Not found"
    if best_score < score_threshold:
        return {
            "answer": "Not found",
            "pages": "N/A",
            "snippet": "N/A"
        }

    # Deduplicate repeating footers and near-identical chunks
    deduped_items = deduplicate_chunks(results_with_scores)

    # Format numbered context chunks [0], [1], ...
    context_blocks = []
    chunk_list = []
    for idx, item in enumerate(deduped_items):
        doc = item["doc"]
        page_num = item["page"]
        chunk_clean = clean_noise(doc.page_content)
        context_blocks.append(f"[{idx}] (Page {page_num})\n{chunk_clean}")
        chunk_list.append(item)

    context_str = "\n\n".join(context_blocks)

    strict_prompt = f"""You are a QA assistant for the Orient BlackSwan History catalogue 2024-25.
Answer ONLY from the numbered context chunks below.

Rules:
1. If the answer is not explicitly stated in the context, set "answer" to "Not found" and "source_ids" to [].
2. Do not use outside knowledge. Do not guess.
3. Opinion or subjective questions (for example 'best book') that the document does not answer must get: "Not found".
4. When writing dates, format them as day month year followed by the original format in brackets, for example: "20 January 2025 (20-01-2025)".
5. Answers must be one short sentence or value (keep it concise and direct).
6. In "source_ids", list ONLY the integer indices (e.g. [0]) of chunks that directly contain the facts used to answer.
7. Return ONLY a valid JSON object in this exact format with no explanation or extra keys:
{{"answer": "<answer or Not found>", "source_ids": [0]}}

Context:
{context_str}

Question: {question}

JSON:"""

    llm = get_llm()
    response = llm.invoke(strict_prompt)
    if hasattr(response, "content"):
        raw_val = response.content
    else:
        raw_val = response

    if isinstance(raw_val, list):
        text_parts = []
        for p in raw_val:
            if isinstance(p, dict) and "text" in p:
                text_parts.append(p["text"])
            elif isinstance(p, str):
                text_parts.append(p)
        raw_text = "".join(text_parts).strip()
    else:
        raw_text = str(raw_val).strip()

    parsed = parse_llm_json(raw_text)
    answer_text = parsed.get("answer", "Not found").strip()
    source_ids = parsed.get("source_ids", [])

    # Check if Not found
    if (answer_text.lower().startswith("not found") or 
        answer_text.lower() == "not found." or 
        not source_ids):
        return {
            "answer": "Not found",
            "pages": "N/A",
            "snippet": "N/A"
        }

    # Build Reference only from chunks in source_ids, deduplicated, sorted, keep at most 3 lowest pages
    used_pages = []
    valid_source_chunks = []
    for sid in source_ids:
        if isinstance(sid, int) and 0 <= sid < len(chunk_list):
            chunk_item = chunk_list[sid]
            used_pages.append(chunk_item["page"])
            valid_source_chunks.append(chunk_item)

    if not used_pages:
        return {
            "answer": "Not found",
            "pages": "N/A",
            "snippet": "N/A"
        }

    sorted_pages = sorted(list(set(used_pages)))[:3]
    page_refs = ", ".join([f"Page {p}" for p in sorted_pages])

    # Snippet comes from the first chunk in source_ids, stripped of noise, max 200 chars
    first_chunk = valid_source_chunks[0]
    clean_snip = clean_noise(first_chunk["doc"].page_content)[:200]

    return {
        "answer": answer_text,
        "pages": page_refs,
        "snippet": clean_snip
    }

def print_result(result: dict):
    print(f"Answer: {result['answer']}")
    print(f"Reference: {result['pages']}")
    print(f"Snippet: {result['snippet']}")

def interactive_cli():
    print("=========================================================")
    print(" Orient BlackSwan History Catalogue 2024-25 QA Assistant ")
    print("=========================================================")
    print("Type your question below (or type 'exit' or 'quit' to stop).\n")

    while True:
        try:
            query = input("Question: ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                print("Goodbye!")
                break
            res = ask(query)
            print("-" * 50)
            print_result(res)
            print("-" * 50 + "\n")
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}\n")

if __name__ == "__main__":
    interactive_cli()
