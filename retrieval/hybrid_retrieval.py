import os
import re
from retrieval.dense_retrieval import get_chroma_collection
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

# Configuration globale des modèles et des seuils de sécurité
MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.50
BM25_THRESHOLD = 1.30

def tokenize(text):
    """Nettoie et tokenise proprement le texte pour BM25 (supprime la ponctuation)."""
    return re.findall(r'\b\w+\b', text.lower())

def hybrid_search(query: str, target_file: str, n_results: int = 2):
    collection = get_chroma_collection()
    model = SentenceTransformer(MODEL_NAME)

    all_data = collection.get(where={"file_name": target_file}, include=["documents", "metadatas"])
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]

    if not documents:
        return []

    tokenized_corpus = [tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    valid_results = []
    
    # --- 1. RECHERCHE DENSE (ChromaDB) ---
    query_embedding = model.encode([query]).tolist()
    dense_results = collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where={"file_name": target_file},
        include=["documents", "metadatas", "distances"]
    )

    dense_texts = dense_results["documents"][0]
    dense_metas = dense_results["metadatas"][0]
    dense_distances = dense_results["distances"][0]

    for text, meta, dist in zip(dense_texts, dense_metas, dense_distances):
        score_sim = 1 / (1 + dist) if dist is not None else 0.0
        if score_sim >= SIMILARITY_THRESHOLD:
            valid_results.append({
                "page": meta.get("page_number", 1),
                "text": text,
                "source": "Dense",
                "score": float(score_sim)
            })

    # --- 2. RECHERCHE LEXICALE (BM25) ---
    tokenized_query = tokenize(query)
    bm25_scores = bm25.get_scores(tokenized_query)
    top_bm25_idx = bm25_scores.argsort()[::-1][:n_results]

    for idx in top_bm25_idx:
        score_bm25 = bm25_scores[idx]
        if score_bm25 >= BM25_THRESHOLD:
            page_num = metadatas[idx].get("page_number", 1)
            
            # 1. On vérifie d'abord si la page n'est pas déjà présente pour cette source
            if not any(res["page"] == page_num and res["source"] == "BM25" for res in valid_results):
                # 2. Si c'est bon, on l'ajoute proprement
                valid_results.append({
                    "page": page_num,
                    "file_name": target_file,
                    "text": documents[idx],
                    "source": "BM25",
                    "score": float(score_bm25)
                })

    return valid_results