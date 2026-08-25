from rag.vector_store import VectorStore
import json
import logging

logger = logging.getLogger(__name__)

def retrieve_patterns(generation_spec, track_id=None):
    """
    Queries ChromaDB with the generation spec to find relevant patterns.
    """
    try:
        vector_store = VectorStore()
        query_text = json.dumps(generation_spec, default=str)
        
        where_filter = None
        if track_id is not None:
            # We filter by specific track_id OR -1 (global rules)
            where_filter = {
                "$or": [
                    {"track_id": int(track_id)},
                    {"track_id": -1}
                ]
            }

        results = vector_store.query(query_text, top_k=5, where_filter=where_filter)
        
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
