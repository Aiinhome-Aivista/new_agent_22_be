import os
import sys
from sentence_transformers import SentenceTransformer

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.vector_store import VectorStore
from db import execute_query

def chunk_text(text, chunk_size=600, overlap=100):
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunks.append(text[start:end])
        if end == text_length:
            break
        start += (chunk_size - overlap)
    return chunks

def ingest_knowledge_base():
    # Fetch ALL standards directly from the database
    db_standards = execute_query("SELECT id, title, description, folder, created_by, track_id FROM architecture_standards")
    
    if not db_standards:
        print("No standards found in database to ingest.")
        return

    vector_store = VectorStore()
    documents = []
    metadatas = []
    ids = []

    for row in db_standards:
        title = row.get('title', '')
        content = row.get('description', '')
        folder = row.get('folder', 'standards')
        created_by = row.get('created_by', '1')
        track_id = row.get('track_id')
        
        if not content:
            continue

        # Determine pattern_type
        pattern_type = "standards"
        if "single_topic" in title.lower():
            pattern_type = "single_topic"
        elif "multi_topic_stateful" in title.lower():
            pattern_type = "multi_topic_stateful"
        elif "error_topic" in title.lower():
            pattern_type = "error_topic"

        if track_id is None:
            track_id = -1

        chunks = chunk_text(content)
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            metadatas.append({
                "filename": f"{title}.md",
                "folder": folder,
                "section_title": f"{title} part {i}",
                "pattern_type": pattern_type,
                "track_id": track_id,
                "created_by": str(created_by)
            })
            ids.append(f"doc_{row['id']}_{i}")

    if documents:
        vector_store.add_documents(documents, metadatas, ids)
        print(f"Ingested {len(documents)} chunks from knowledge base (DB).")
    else:
        print("No content found in knowledge base (DB).")

if __name__ == "__main__":
    ingest_knowledge_base()
