from rag.vector_store import VectorStore
import json
import logging

logger = logging.getLogger(__name__)

def retrieve_patterns(generation_spec):
    """
    Queries ChromaDB with the generation spec to find relevant patterns.
    """
    try:
        vector_store = VectorStore()
        query_text = json.dumps(generation_spec, default=str)
        results = vector_store.query(query_text, top_k=5)
        
        matches = []
        if results and results.get("documents") and len(results["documents"]) > 0:
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            dists = results["distances"][0]
            
            for doc, meta, dist in zip(docs, metas, dists):
                similarity = 1.0 - dist # approx
                matches.append({
                    "pattern_type": meta.get("pattern_type", "standards"),
                    "source_reference": meta.get("filename", "unknown"),
                    "similarity_score": similarity,
                    "cited_text": doc
                })
        return matches
    except Exception as e:
        logger.error(f"Error retrieving patterns: {e}")
        return []
