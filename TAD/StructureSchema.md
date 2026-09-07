
📂 Structure du Projet

DocumentExtractor/
├── config.py                 # Hyperparamètres et configurations globales
├── conftest.py               # Configuration des chemins d'importation Pytest
├── models.py                 # Schémas de données Pydantic (ExtractionReport, etc.)
├── pre_checker.py            # Phase 1: Contrôle d'intégrité physique
├── quality_checker.py        # Phase 3: Évaluation heuristique de lisibilité
├── pipeline.py               # Orchestrateur du pipeline & Exécuteur de batch
├── main.py                   # Script de démonstration E2E & Générateur JSON
├── extractors/
│   ├── __init__.py
│   ├── base.py               # Interface abstraite BaseExtractor
│   ├── txt_extractor.py      # Stratégie d'extraction TXT (chardet)
│   └── pdf_extractor.py      # Stratégie d'extraction PDF (PyPDF)
└── tests/
    └── test_pipeline.py      # Suite de tests unitaires et d'intégration