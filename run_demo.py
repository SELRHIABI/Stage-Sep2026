import json
from chunking.chunking_pipeline import ChunkingEngine, CONFIG_A, CONFIG_B

# Données de test simulant la sortie du DocumentExtractor
sample_extraction = {
    "filename": "HPS_Report.pdf",
    "extension": "pdf",
    "pages": [
        {
            "page_number": 1,
            "text": (
                "Le système HPS assure le traitement sécurisé des transactions de paiement électronique. "
                "Il intègre des modules de détection de fraude en temps réel basés sur l'intelligence artificielle. "
                "Chaque transaction est analysée en moins de 50 millisecondes afin d'évaluer le niveau de risque. "
                "En cas de détection d'anomalie, la transaction est soit soumise à une vérification 3D-Secure, "
                "soit purement et simplement rejetée selon les règles définies par l'émetteur."
            )
        }
    ]
}

# Execution Config A
engine_a = ChunkingEngine(CONFIG_A["chunk_size"], CONFIG_A["chunk_overlap"])
chunks_a = engine_a.process_document(sample_extraction)

# Execution Config B
engine_b = ChunkingEngine(CONFIG_B["chunk_size"], CONFIG_B["chunk_overlap"])
chunks_b = engine_b.process_document(sample_extraction)

# Affichage des résultats
print("=== RÉSULTATS DU BENCHMARK ===")
print(f"Taille originale du texte : {len(sample_extraction['pages'][0]['text'])} caractères")
print(f"Nombre de chunks générés (Config A - 300/50) : {len(chunks_a)}")
print(f"Nombre de chunks générés (Config B - 1000/150) : {len(chunks_b)}\n")

print("=== EXEMPLE DE CHUNK GÉNÉRÉ (Config A) ===")
if chunks_a:
    print(json.dumps(chunks_a[0].model_dump(), indent=2, ensure_ascii=False))