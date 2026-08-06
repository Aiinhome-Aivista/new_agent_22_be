import os
import sys
from sentence_transformers import SentenceTransformer

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.vector_store import VectorStore

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
    kb_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'knowledge_base')
    if not os.path.exists(kb_dir):
        print(f"Knowledge base directory {kb_dir} not found.")
        return

    vector_store = VectorStore()
    documents = []
    metadatas = []
    ids = []

    file_id = 0
    for root, dirs, files in os.walk(kb_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Determine pattern_type
                pattern_type = "standards"
                if "single_topic" in file:
                    pattern_type = "single_topic"
                elif "multi_topic_stateful" in file:
                    pattern_type = "multi_topic_stateful"
                elif "error_topic" in file:
                    pattern_type = "error_topic"

                chunks = chunk_text(content)
                for i, chunk in enumerate(chunks):
                    documents.append(chunk)
                    metadatas.append({
                        "filename": file,
                        "section_title": f"{file} part {i}",
                        "pattern_type": pattern_type
                    })
                    ids.append(f"doc_{file_id}_{i}")
                
                file_id += 1

    if documents:
        vector_store.add_documents(documents, metadatas, ids)
        print(f"Ingested {len(documents)} chunks from knowledge base.")
    else:
        print("No markdown files found in knowledge base.")

if __name__ == "__main__":
    ingest_knowledge_base()
