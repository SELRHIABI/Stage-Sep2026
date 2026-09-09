from retrieval.dense_retrieval import DenseRetrievalPipeline

SUMMARY_PATH = "summary/summary_report.json"


def run_tests():
    # 1. Initialisation du pipeline (charge le modèle embedding + ChromaDB)
    pipeline = DenseRetrievalPipeline()

    # 2. Chargement et validation des 12 chunks
    chunks = pipeline.load_and_validate_chunks(SUMMARY_PATH)
    if not chunks:
        print("❌ Aucun chunk chargé.")
        return

    # 3. Indexation dans ChromaDB
    pipeline.ingest_chunks(chunks)

    # 4. Requêtes de test adaptées au document HPS
    queries = [
        "Fondée en 1995 par un groupe d'experts marocains en monétique",
        "Quels sont les services ou solutions de HPS ?",
        "Quelle est la recette de la tarte aux pommes ?",
    ]

    print("\n" + "=" * 50)
    print("🚀 EXÉCUTION DES TESTS DE RECHERCHE DENSE")
    print("=" * 50)

    for i, q in enumerate(queries, 1):
        print(f"\n🔍 Test #{i} : '{q}'")
        results = pipeline.search(q, top_k=2)

        for res in results:
            page = res.metadata.get("page_number", "N/A")
            preview = res.content[:120].replace("\n", " ")

            print(
                f"  Rang {res.rank} | Score: {res.similarity_score} | Chunk: {res.chunk_id} (Page {page})"
            )
            print(f'  Extrait: "{preview}..."')


if __name__ == "__main__":
    run_tests()