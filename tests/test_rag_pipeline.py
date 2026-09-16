import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from retrieval.hybrid_retrieval import hybrid_search
from generation.llm_generation import generate_rag_response

def run_rag_pipeline():
    target_file = "test2.pdf"
    
    
    query = "Quels sont les défis liés à l'évaluation de la performance d'un système RAG ?"
    
    print("=" * 70)
    print(f"🔎 Étape 1 : Recherche hybride pour la requête : '{query}'")
    print("=" * 70)
    
    valid_fragments = hybrid_search(query, target_file, n_results=2)
    
    for res in valid_fragments:
        print(f"   ├─ Page : {res['page']} | Source : {res['source']} | Score : {res['score']:.4f}")

    print("\n" + "=" * 70)
    print("🤖 Étape 2 : Génération de la réponse avec Ollama")
    print("=" * 70)
    
    generate_rag_response(query, valid_fragments)

if __name__ == "__main__":
    run_rag_pipeline()