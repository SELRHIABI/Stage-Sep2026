import os
import sys
import re

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from retrieval.dense_retrieval import get_chroma_collection
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

MODEL_NAME = "all-MiniLM-L6-v2"
SIMILARITY_THRESHOLD = 0.50
BM25_THRESHOLD = 1.30  # Seuil minimal pour valider BM25

def tokenize(text):
    """Nettoie et tokenise proprement le texte pour BM25 (supprime la ponctuation)."""
    return re.findall(r'\b\w+\b', text.lower())

def run_hybrid_tests():
    target_file = "test2.pdf"
    collection = get_chroma_collection()
    model = SentenceTransformer(MODEL_NAME)

    # Récupération de tous les documents pour initialiser BM25
    all_data = collection.get(where={"file_name": target_file}, include=["documents", "metadatas"])
    documents = all_data["documents"]
    metadatas = all_data["metadatas"]

    tokenized_corpus = [tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    total_chunks = len(documents)

    print("=" * 70)
    print("🚀 ÉVALUATION RAG - RECHERCHE HYBRIDE SÉCURISÉE (DENSE + BM25)")
    print("=" * 70)
    print(f"📊 Fragments indexés : {total_chunks} | Seuil Dense : {SIMILARITY_THRESHOLD} | Seuil BM25 : {BM25_THRESHOLD}\n")

    test_categories = [
        {
            "type": "Mots exacts (Nom propre)",
            "query": "LangGraph",
            "expected_page": 7
        },
        {
            "type": "Phrase reformulée",
            "query": "Quels frameworks permettent d'évaluer la performance d'un pipeline RAG ?",
            "expected_page": 9
        },
        {
            "type": "Hors contexte",
            "query": "Quelles sont les règles de maintenance d'un moteur d'avion ?",
            "expected_page": None
        }
    ]

    for item in test_categories:
        test_type = item["type"]
        query = item["query"]

        print("=" * 70)
        print(f"🧪 Test [{test_type}] - Requête : '{query}'")
        print("-" * 70)

        # --- 1. RECHERCHE LEXICALE (BM25) ---
        tokenized_query = tokenize(query)
        bm25_scores = bm25.get_scores(tokenized_query)
        top_bm25_idx = bm25_scores.argsort()[::-1][:2]

        print("📌 [RÉSULTATS RECHERCHE LEXICALE BM25]")
        bm25_valid_found = False
        for j, idx in enumerate(top_bm25_idx):
            rang = j + 1
            meta = metadatas[idx]
            text = documents[idx]
            page_num = meta.get("page_number", 1)
            score_bm25 = bm25_scores[idx]
            
            if score_bm25 >= BM25_THRESHOLD:
                bm25_valid_found = True
                statut = "✅ RETENU (Pertinent)"
            else:
                statut = "❌ REJETÉ (Sous le seuil BM25)"

            fragment_propre = text.strip().replace("\n", " ")

            print(f"   ├─ Rang           : {rang}")
            print(f"   ├─ Numéro de page : {page_num}")
            print(f"   ├─ Score (BM25)   : {score_bm25:.4f} -> {statut}")
            print(f"   └─ Fragment       : {fragment_propre[:100]}...")
            if rang == 1:
                print()

        # --- 2. RECHERCHE DENSE (ChromaDB) ---
        query_embedding = model.encode([query]).tolist()
        dense_results = collection.query(
            query_embeddings=query_embedding,
            n_results=2,
            where={"file_name": target_file},
            include=["documents", "metadatas", "distances"]
        )

        dense_texts = dense_results["documents"][0]
        dense_metas = dense_results["metadatas"][0]
        dense_distances = dense_results["distances"][0]

        print("📌 [RÉSULTATS RECHERCHE DENSE]")
        dense_valid_found = False
        for j, (text, meta, dist) in enumerate(zip(dense_texts, dense_metas, dense_distances)):
            rang = j + 1
            page_num = meta.get("page_number", 1)
            
            score_sim = 1 / (1 + dist) if dist is not None else 0.0
            fragment_propre = text.strip().replace("\n", " ")

            if score_sim >= SIMILARITY_THRESHOLD:
                dense_valid_found = True
                statut = "✅ RETENU (Pertinent)"
            else:
                statut = "❌ REJETÉ (Sous le seuil Dense)"

            print(f"   ├─ Rang           : {rang}")
            print(f"   ├─ Numéro de page : {page_num}")
            print(f"   ├─ Score (Sim.)   : {score_sim:.4f} -> {statut}")
            print(f"   └─ Fragment       : {fragment_propre[:100]}...")
            if rang == 1:
                print()

        if not dense_valid_found and not bm25_valid_found:
            print("🛡️ [FILTRE ACTIF] Aucun fragment n'a atteint les seuils requis. Réponse refusée pour éviter l'hallucination.\n")
        else:
            print()

if __name__ == "__main__":
    run_hybrid_tests()