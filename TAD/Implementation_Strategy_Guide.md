# DocumentExtractor — Implementation Strategy Guide
**Document Design Document & Architecture Roadmap**

---

## 1. The Core Idea

**DocumentExtractor** repose sur le principe d'**Ingestion Résiliente Contrainte par le Métier**. L'objectif est de séparer l'étape de validation d'intégrité de l'étape de parsing pur pour éviter tout plantage global du système (`zero-crash architecture`). 

Le système ne suppose jamais qu'un document est valide. Chaque fichier entrant suit un circuit d'isolation : il passe par des filtres de vérification (taille, en-tête de fichier, extensions), est orienté vers un extracteur spécialisé encapsulé dans une stratégie d'exécution isolée, puis subit une évaluation heuristique de qualité. Si un document est corrompu, vide ou illisible, l'erreur est capturée à chaud et transformée en métadonnée d'échec sans interrompre la boucle principale.

```text
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│ Input Documents │ ──> │ Physical Check   │ ──> │ Isolated Parsing  │ ──> │ Quality Scoring   │
│ (PDF / TXT)     │     │ (Size, Extension)│     │ (Pdf/Txt Strategy)│     │ & Metadata Schema │
└─────────────────┘     └──────────────────┘     └───────────────────┘     └───────────────────┘
```

---

## 2. Technical Stack Matrix

| Outil / Library | Rôle dans l'Architecture | Raisons du Choix Technique |
| :--- | :--- | :--- |
| **Python 3.10+** | Runtime Principal | Gestion native avancée des types (`typing`), des `dataclasses` et support moderne du multitraitement. |
| **PyPDF** | Engine de Parsing PDF | Bibliothèque pure-Python, légère, sans dépendances C lourdes, idéale pour extraire texte et métadonnées page par page. |
| **chardet** | Détecteur d'Encodage TXT | Analyse statistique de la distribution des octets pour identifier l'encodage (UTF-8, Latin-1, CP1252) avant lecture. |
| **pydantic (v2)** | Validation & Schéma de Données | Typage strict à l'exécution, validation d'attributs et sérialisation JSON haute performance. |
| **pytest** | Framework de Test Unitaire & E2E | Automatisation des tests de régression, gestion des fixtures pour générer des fichiers corrompus/vides. |
| **structlog / logging** | Structured Observability | Traçabilité JSON des logs d'exécution pour suivre les erreurs par document en environnement de production. |

---

## 3. Global Pipeline Architecture

```text
                               ┌───────────────────────────┐
                               │   Incoming Document File  │
                               └─────────────┬─────────────┘
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   Stage 1: Pre-Checker    │
                               │  - Exist? Size > 0? Ext?  │
                               └─────────────┬─────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │ Valid                                     │ Invalid
                       ▼                                           ▼
         ┌───────────────────────────┐               ┌───────────────────────────┐
         │ Stage 2: Format Router    │               │  Stage 2b: Early Error    │
         └─────────────┬─────────────┘               │  Flag Status = REJECTED   │
                       │                             └─────────────┬─────────────┘
          ┌────────────┴────────────┐                              │
          ▼                         ▼                              │
┌──────────────────┐      ┌──────────────────┐                     │
│ PDF Extractor    │      │ TXT Extractor    │                     │
│ - PyPDF Strategy │      │ - Chardet Read   │                     │
└─────────┬────────┘      └─────────┬────────┘                     │
          │                         │                              │
          └────────────┬────────────┘                              │
                       │ Extracted Text & Raw Meta                 │
                       ▼                                           │
         ┌───────────────────────────┐                             │
         │ Stage 3: Quality Scoring  │                             │
         │ - Alpha-Ratio & Metrics   │                             │
         └─────────────┬─────────────┘                             │
                       │                                           │
                       ▼                                           │
         ┌───────────────────────────┐                             │
         │ Stage 4: Schema Builder   │ ◄───────────────────────────┘
         │ - Pydantic Validation     │
         └─────────────┬─────────────┘
                       │
                       ▼
         ┌───────────────────────────┐
         │   Final ExtractionReport  │
         └───────────────────────────┘
```

---

## 4. Step-by-Step Implementation Detail

### Stage 1: Pre-Checker & Physical Validation
* **Description :** Analyse le fichier sur le système de disque sans ouvrir entièrement le contenu en mémoire.
* **Checks :** Existence du chemin, taille en octets (size > 0), vérification de l'extension contre la liste blanche (`.pdf`, `.txt`).
* **Edge Cases & Error Handling :** Fichier introuvable (`FileNotFoundError`), fichier de 0 octet (`EmptyFileError`), extension non supportée (`UnsupportedFormatError`). Le pipeline attrape ces exceptions et redirige immédiatement vers la création d'un rapport d'échec.
> **AI tip — why :** *Exécuter ces vérifications atomiques en amont évite d'instancier des parsers lourds en mémoire pour des fichiers inutilisables, optimisant ainsi le débit global du système.*

### Stage 2: Strategy-Based Parsing Engine
* **Description :** Traite le document selon sa nature via un design pattern *Strategy*.
  * **Pour le TXT :** `chardet` inspecte le flux binaire d'entrée pour identifier l'encodage. Le fichier est ensuite lu sous cet encodage sans planter sur des caractères mal formés (`errors='replace'`).
  * **Pour le PDF :** `PyPDF` charge le document. Une boucle parcourt le document page par page pour isoler l'extraction textuelle et comptabiliser les métadonnées spécifiques à chaque page.
* **Edge Cases & Error Handling :** PDF protégé par mot de passe (`FileEncryptedError`), PDF corrompu ou incomplet (`PdfReadError`), fichier texte binaire déguisé. Chaque cas d'erreur est capturé localement par le composant et converti en statut d'erreur explicite.
> **AI tip — why :** *Extraire le PDF page par page plutôt que globalement garantit que si la page 10 est corrompue, les pages 1 à 9 restent correctement extraites et conservées.*

### Stage 3: Quality Scoring Engine
* **Description :** Calcule un score heuristique de qualité compris entre 0 et 100 en évaluant la lisibilité du texte extrait.
  * **Invariants :** Score = (Caractères Alphanumériques et Espace / Nombre Total de Caractères) * 100.
  * **Drapeaux de statut :** 
    * Score >= 80 : `HIGH_QUALITY`
    * 50 <= Score < 80 : `MEDIUM_QUALITY`
    * Score < 50 ou Texte Vide : `SUSPICIOUS_OR_SCAN`
* **Edge Cases & Error Handling :** Division par zéro évitée si le nombre total de caractères est égal à zéro (attribution directe du score 0.0).
> **AI tip — why :** *Un PDF scanné (image) renvoie souvent une chaîne vide ou du bruit d'encodage. Ce score de qualité permet de filtrer automatiquement les documents nécessitant un traitement OCR ultérieur sans faire chuter le pipeline.*

### Stage 4: Output Schema & Report Generation
* **Description :** Agrège l'ensemble des données (texte, aperçu de 200 caractères max, métadonnées, scores) dans un modèle Pydantic strict pour produire une sortie normalisée au format dict/JSON.

---

## 5. Parallelism, Scaling, and Resource Management

```text
                     ┌──────────────────────────────┐
                     │    Document Batch Queue      │
                     └──────────────┬───────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  ▼                                   ▼
       ┌────────────────────┐              ┌────────────────────┐
       │ Process Worker 1   │              │ Process Worker 2   │
       │ (Doc 1 -> Stage 1-4)│              │ (Doc 2 -> Stage 1-4)│
       └────────────────────┘              └────────────────────┘
```

* **Concurrence basée sur les Processus :** L'extraction de texte et le parsing PDF sont des opérations dépendantes du CPU (`CPU-bound`). Le module doit utiliser `concurrent.futures.ProcessPoolExecutor` au lieu du multithreading pour contourner le Global Interpreter Lock (GIL) de Python.
* **Gestion Mémoire :** Pour traiter des fichiers volumineux sans dépasser la mémoire vive, les gros fichiers PDF doivent être lus en mode streaming ou traités page par page avec libération mémoire explicite.
* **Isolation :** En cas d'erreur fatale non interceptée au niveau C dans une sous-librairie, l'utilisation de processus isolés permet d'éviter la fermeture du processus principal.

---

## 6. Configuration Variables & Hyperparameters

| Variable | Type | Valeur par Défaut | Description |
| :--- | :--- | :--- | :--- |
| `MAX_FILE_SIZE_MB` | `int` | `50` | Taille maximale autorisée pour un document avant rejet préalable. |
| `PREVIEW_CHAR_LIMIT` | `int` | `200` | Nombre maximal de caractères à conserver pour l'aperçu du texte. |
| `QUALITY_THRESHOLD_HIGH` | `float` | `80.0` | Seuil minimal pour considérer un document comme de haute qualité. |
| `QUALITY_THRESHOLD_LOW` | `float` | `50.0` | Seuil en dessous duquel le document est classé comme suspect/scan. |
| `DEFAULT_TXT_ENCODING` | `str` | `"utf-8"` | Encodage par défaut de repli si la détection par `chardet` échoue. |
| `SUPPORTED_EXTENSIONS` | `List[str]` | `[".pdf", ".txt"]` | Liste des extensions de fichiers autorisées dans le pipeline. |

---

## 7. Cost & Resource Tracking Strategy

* **Coût Compute Local :** Le projet n'utilise pas d'API payante externe (LLM ou OCR cloud). Le coût d'exécution est exclusivement lié au temps CPU/RAM local.
* **Indicateur de Performance (Benchmark) :** Le pipeline doit instrumenter chaque traitement avec un chronomètre haute précision (`time.perf_counter()`).
* **Métriques à tracer :**
  * `Execution_Time_ms` : temps pris par document.
  * `Memory_Peak_MB` : consommation mémoire maximale pendant l'extraction.
  * `Throughput_Docs_Per_Sec` : nombre de documents traités par seconde sur un lot.

---

## 8. Phased Implementation Roadmap

```text
Phase 1: Architecture Core   [██████████] Week 1
Phase 2: Robustness Engine   [██████████] Week 2
Phase 3: Integration & Tests [██████████] Week 3
```

### Semaine 1 : Architecture Core & Strategies
* **Objectif :** Poser la structure orientée objet et les extracteurs de base.
* **Tâches :**
  1. Configurer l'environnement de développement et les modèles Pydantic (`ExtractionReport`, `PageMetadata`).
  2. Implémenter l'extracteur TXT avec détection d'encodage via `chardet`.
  3. Implémenter l'extracteur PDF page par page via `PyPDF`.

### Semaine 2 : Résilience & Engine de Qualité
* **Objectif :** Implémenter la gestion des erreurs et l'indicateur de qualité.
* **Tâches :**
  1. Construire le composant `QualityChecker` et régler la formule d'évaluation du score.
  2. Ajouter les garde-fous de la Phase 1 (fichiers vides, extensions invalides, exceptions de parsing).
  3. Valider la non-interruption du programme lors du traitement d'un dossier mixte.

### Semaine 3 : Parallélisation, Tests & Documentation
* **Objectif :** Finaliser le projet pour la démonstration d'entreprise chez SG ABS.
* **Tâches :**
  1. Intégrer `ProcessPoolExecutor` pour le traitement par lot.
  2. Rédiger la suite de tests automatisés sous `pytest`.
  3. Produire le fichier `README.md` et préparer le script de démonstration `main.py`.

---

## 9. Validation Test Protocol

### Test Case 1 : Document Valide Multi-Pages (PDF)
* **Entrée :** Fichier `sample_valid.pdf` (3 pages de texte standard).
* **Résultat Attendu :** `status = "SUCCESS"`, `total_chars > 0`, `len(pages) == 3`, `quality_score > 80.0` (`HIGH_QUALITY`).

### Test Case 2 : Fichier Invalide / Corrompu (Edge Case)
* **Entrée :** Fichier `corrupted.pdf` (fichier texte arbitraire renommé en `.pdf` ou binaire tronqué).
* **Résultat Attendu :** Le programme ne crashe pas. `status = "FAILED"`, `error_message` contient une description claire de l'erreur (`PdfReadError` intercepté), `quality_score = 0.0`.

### Test Case 3 : Fichier Vide (Edge Case)
* **Entrée :** Fichier `empty.txt` (0 octet sur le disque).
* **Résultat Attendu :** Le programme filtre le fichier dès la Phase 1. `status = "FAILED"`, `error_message = "Fichier vide (0 octet)"`.

---

## 10. Summary

Le projet **DocumentExtractor** constitue une solution légère, modulaire et hautement résiliente conçue pour traiter des flux de documents hétérogènes sans interruption de service. En combinant un découpage par stratégies (PyPDF pour le PDF, Chardet pour le TXT), un filtrage préventif des fichiers invalides et un moteur de scoring de qualité heuristique, cette architecture garantit l'extraction fiable des textes et métadonnées tout en isolant complètement les erreurs de parsing. Ce guide fournit au stagiaire la feuille de route technique exacte pour livrer un code propre, testable et conforme aux exigences d'ingénierie logicielle d'une structure comme SG ABS.
