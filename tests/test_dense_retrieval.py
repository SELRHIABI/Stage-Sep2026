import os
import sys

# Ajout du chemin racine pour que Python trouve le dossier 'retrieval'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 1. IMPORTATION CORRIGÉE : On importe la fonction officielle du pipeline
from retrieval.hybrid_retrieval import hybrid_search, SIMILARITY_THRESHOLD, BM25_THRESHOLD

def run_hybrid_tests():
    target_file = "test2.pdf"

    print("=" * 70)
    print("🚀 ÉVALUATION RAG - RECHERCHE HYBRIDE SÉCURISÉE (DENSE + BM25)")
    print("=" * 70)
    print(f"📊 Seuil Dense : {SIMILARITY_THRESHOLD} | Seuil BM25 : {BM25_THRESHOLD}\n")

    test_categories = [
        {"type": "Mots exacts (Nom propre)", "query": "LangGraph"},
        {"type": "Phrase reformulée", "query": "Quels frameworks permettent d'évaluer la performance d'un pipeline RAG ?"},
        {"type": "Hors contexte", "query": "Quelles sont les règles de maintenance d'un moteur d'avion ?"}
    ]

    for item in test_categories:
        print("=" * 70)
        print(f"🧪 Test [{item['type']}] - Requête : '{item['query']}'")
        print("-" * 70)

        # Appel direct à la fonction officielle du pipeline
        results = hybrid_search(item['query'], target_file, n_results=2)

        if not results:
            print("🛡️ [FILTRE ACTIF] Aucun fragment n'a atteint les seuils requis. Réponse refusée pour éviter l'hallucination.\n")
        else:
            for j, res in enumerate(results):
                rang = j + 1
                print(f"   ├─ Rang           : {rang}")
                print(f"   ├─ Numéro de page : {res['page']}")
                print(f"   ├─ Moteur source  : {res['source']}")
                print(f"   ├─ Score          : {res['score']:.4f} -> ✅ RETENU")
                print(f"   └─ Fragment       : {res['text'].strip().replace('\n', ' ')[:100]}...\n")

if __name__ == "__main__":
    run_hybrid_tests()