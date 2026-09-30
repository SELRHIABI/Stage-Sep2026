import os
from rank_bm25 import BM25Okapi

def test_word_search():
    # 1. Simuler ou charger les fragments de ton document PDF source
    # (Dans ton pipeline réel, ces fragments proviennent de ton extraction de document)
    documents = [
        {"page": 1, "text": "Introduction au RAG (Retrieval-Augmented Generation) Le RAG est une architecture d'intelligence artificielle qui combine la puissance des Grands Modèles de Langage (LLM) avec la précision d'un système de recherche documentaire externe."},
        {"page": 1, "text": "Le rôle de LangChain LangChain est un framework de développement puissant qui facilite grandement la création d'applications basées sur des LLM."},
        {"page": 1, "text": "Architecture typique d'un pipeline RAG Le flux de travail s'articule généralement autour de deux grandes étapes : indexation et interrogation."}
    ]

    # 2. Mot-clé recherché
    query_word = "et"
    print(f"🔎 Test de recherche par mot-clé pour : '{query_word}'\n")

    # 3. Préparation du corpus pour BM25 (tokenisation simple par mots)
    tokenized_corpus = [doc["text"].lower().split() for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)

    # 4. Exécution de la recherche lexicale
    tokenized_query = query_word.lower().split()
    scores = bm25.get_scores(tokenized_query)

    # 5. Affichage des résultats
    for i, doc in enumerate(documents):
        print(f"📄 Page {doc['page']} | Score BM25 : {scores[i]:.4f}")
        print(f"   Extrait : {doc['text'][:80]}...\n")

if __name__ == "__main__":
    test_word_search()