import chromadb
from sentence_transformers import SentenceTransformer
from config import CHROMA_PERSIST_DIR, EMBEDDING_MODEL
import logging

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self.collection = self.client.get_or_create_collection(name="agent22_knowledge_base")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}")

    def add_documents(self, documents, metadatas, ids):
        try:
            embeddings = self.embedding_model.encode(documents).tolist()
            self.collection.add(
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added {len(documents)} documents to vector store.")
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}")

    def query(self, text, top_k=5):
        try:
            query_embedding = self.embedding_model.encode([text]).tolist()
            results = self.collection.query(
                query_embeddings=query_embedding,
                n_results=top_k
            )
            return results
        except Exception as e:
            logger.error(f"Error querying vector store: {e}")
            return {"documents": [], "metadatas": [], "distances": []}
