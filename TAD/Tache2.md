# DocumentExtractor

DocumentExtractor est un outil Python permettant d'extraire, de vérifier la qualité et de structurer le texte contenu dans des fichiers TXT et PDF.

---

1. Description de l'architecture
Le traitement d'un document suit quatre étapes successives :
1.1 Validation du fichier (existence, taille non nulle, extension autorisée).
1.2 Extraction du texte (détection d'encodage pour TXT, lecture page par page pour PDF).
1.3 Calcul d'un score de qualité du texte extrait.
1.4 Génération d'un rapport structuré au format JSON avec Pydantic.

Le traitement de plusieurs fichiers en parallèle est pris en compte.

---

2. Prérequis
- Python version 3.10 ou supérieure.

---

3. Installation
3.1 Ouvrir un terminal dans le dossier du projet.
3.2 Créer un environnement virtuel :
    - Sur Windows : python -m venv .venv
    - Sur Linux ou macOS : python3 -m venv .venv
3.3 Activer l'environnement virtuel :
    - Sur Windows (PowerShell) : .\.venv\Scripts\Activate.ps1
    - Sur Linux ou macOS : source .venv/bin/activate
3.4 Installer les dépendances :
    pip install pypdf chardet pydantic pytest

---

4. Structure des fichiers
- config.py : Configuration globale du projet.
- conftest.py : Configuration des chemins d'importation pour les tests.
- models.py : Définition des structures de données (Pydantic).
- pre_checker.py : Module de vérification des fichiers.
- quality_checker.py : Module d'évaluation de la qualité du texte.
- pipeline.py : Orchestrateur du traitement.
- main.py : Script de démonstration et d'export JSON.
- extractors/ : Contient les scripts d'extraction pour TXT et PDF.
- tests/ : Contient la suite de tests unitaires.

---

5. Lancement de la démonstration
Exécuter la commande suivante pour tester le projet sur un jeu de fichiers d'exemple :
python main.py

Un fichier récapitulatif sera généré dans ./test_docs/summary_report.json.

---

6. Exécution des tests automatisés
Pour vérifier le bon fonctionnement de l'ensemble du code avec Pytest, lancer :
python -m pytest