# Implementation Strategy Guide : Pipeline de Chunking & Structuration de Métadonnées RAG

## 1. The Core Idea

L'objectif de cette étape est de transformer le texte brut et structuré produit par le pipeline `DocumentExtractor` en unités d'information sémantiquement cohérentes appelées **chunks** (ou fragments). Dans une architecture RAG (*Retrieval-Augmented Generation*), le découpage est l'étape critique qui conditionne la précision de la recherche vectorielle et la qualité de la génération par le LLM.

Pour garantir une architecture *Zero-Crash*, modulable et résiliente, nous adoptons une approche fondée sur le pattern **Text Splitter Layer** couplé à une **Normalisation des Métadonnées par Schéma Strict (Pydantic)**. Le texte issu du rapport JSON initial est segmenté de manière déterministe tout en propageant l'intégralité du contexte source (provenance, type de document, pagination originale, volumétrie).

### Schéma Conceptuel

```text
[ DocumentExtractor JSON Output ]
               │
               ▼
   [ Text Splitter Component ] ──(Chunking Strategy: Size + Overlap)
               │
               ▼
  [ Metadata Injection Engine ] ──(UUID + Page Mapping + Char Counter)
               │
               ▼
[ Validated Pydantic Chunks Schema ]
               │
               ▼
[ Vector Storage Ready Payload ]
```

---

## 2. Technical Stack Matrix

| **Outil / Bibliothèque** | **Rôle dans l'Architecture** | **Raisons du Choix Technique** |
|---|---|---|
| **LangChain Text Splitters** (`RecursiveCharacterTextSplitter`) | Composant principal de découpage textuel. | Découpage hiérarchique priorisant les paragraphes (`\n\n`), lignes (`\n`), mots (` `) et caractères (`""`) pour préserver la cohérence sémantique. |
| **Pydantic v2** | Validation de schéma et typage strict des fragments (`ChunkSchema`). | Sérialisation JSON rapide, garantie d'intégrité des données avant stockage vectoriel et gestion d'erreurs au niveau du type. |
| **UUID** (`uuid.uuid4`) | Génération des identifiants uniques de fragments. | Identifiants uniques permettant le suivi d'audit, l'indexation unique et l'invalidation dans la base vectorielle. |
| **Pytest** | Suite de tests automatisés et benchmarks de configurations. | Évaluation comparative des hyperparamètres de découpage et validation des edge cases. |

---

## 3. Global Pipeline Architecture

```text
+-----------------------------------------------------------------------------------+
|                            STAGE 1: INPUT INGESTION                               |
|  - Lecture du rapport JSON d'extraction (DocumentExtractor output)                |
|  - Extraction du texte brut et des métadonnées de haut niveau (nom, extension)    |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                         STAGE 2: TEXT SPLITTING ENGINE                            |
|  - Instanciation du RecursiveCharacterTextSplitter (Config A vs Config B)         |
|  - Segmentation contextuelle du texte par page ou par document global             |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                      STAGE 3: METADATA & ID ENRICHMENT                            |
|  - Génération d'un UUID unique par chunk (ex: `chunk_doc_001_p1_a8f9`)            |
|  - Association des métadonnées : nom source, type, page_number, char_count        |
+-----------------------------------------------------------------------------------+
                                          │
                                          ▼
+-----------------------------------------------------------------------------------+
|                        STAGE 4: SCHEMA VALIDATION & OUTPUT                        |
|  - Instanciation du modèle Pydantic `DocumentChunk`                               |
|  - Validation de la contrainte char_count >= min_threshold                        |
|  - Export au format JSON structuré prêt pour l'indexation vectorielle              |
+-----------------------------------------------------------------------------------+
```

---

## 4. Step-by-Step Implementation Detail

### Stage 1 : Ingestion & Pre-Processing

Ce module lit les rapports `ExtractionReport` générés précédemment. Si le document ne contient aucun texte (`quality_label == "SUSPICIOUS_OR_SCAN"` ou `total_chars == 0`), le pipeline contourne le découpage pour éviter de polluer l'index vectoriel avec des fragments vides.

> **AI tip — why :** *Traiter des documents sans texte exploitable génère des artefacts d'embeddings inutiles en base vectorielle, ce qui dégrade le score de pertinence lors du COSINE Similarity Search.*

---

### Stage 2 : Configurable Splitting Strategy

Nous implémentons deux configurations distinctes qu'il convient de benchmarquer :

- **Configuration A (Granularité fine) :** `chunk_size = 300`, `chunk_overlap = 50`.  
  Idéale pour les réponses très factuelles ou les questions/réponses précises.

- **Configuration B (Contextuelle / Paragraphe) :** `chunk_size = 1000`, `chunk_overlap = 150`.  
  Adaptée à la conservation du contexte long (ex: analyses de rapports complexes comme `HPS.pdf`).

---

### Stage 3 : Structuration Pydantic & Identifiants

Chaque fragment produit est transformé en un objet strict respectant le schéma `ChunkModel` :

- `chunk_id`: `str` (UUIDv4)
- `content`: `str`
- `source_document`: `str`
- `document_type`: `str` (ex: `pdf`, `txt`)
- `page_number`: `Optional[int]`
- `char_count`: `int`

> **AI tip — why :** *Conserver explicitement le* `page_number` *dans les métadonnées de chaque chunk est indispensable en production pour permettre le "source attribution" (afficher la page exacte d'où provient l'information dans l'interface utilisateur).*

---

### Edge Cases & Stratégie de Résilience

- **Fichiers sans numéro de page (ex: `.txt`) :**  
  La propriété `page_number` doit valoir `None` ou `1` sans lever d'exception.

- **Taille de fragment supérieure à `chunk_size` :**  
  Se produit si un mot ou une chaîne ininterrompue dépasse la taille maximale. Le découpeur applique une stratégie de repli (*fallback*) en coupant au caractère pur sans faire planter le script.

- **Chevauchement supérieur à la taille du fragment :**  
  Le système de configuration doit rejeter à l'instanciation tout paramètre où `chunk_overlap >= chunk_size`.

---

## 5. Parallelism, Scaling, and Resource Management

```text
[ Master Process ] ──► [ ProcessPoolExecutor ] ──► [ Worker 1 : Chunking Doc A ]
                                              ──► [ Worker 2 : Chunking Doc B ]
                                              ──► [ Worker 3 : Chunking Doc C ]
```

- **Nature de la charge :**  
  Le découpage de texte par expressions régulières et comptage de caractères est une opération **CPU-bound**.

- **Stratégie d'exécution :**  
  Utilisation de `ProcessPoolExecutor` pour distribuer le découpage par lot de documents sur plusieurs cœurs CPU.

- **Gestion mémoire :**  
  Traitement sous forme de générateurs (*Iterators*). Au lieu de charger l'ensemble des fragments de milliers de documents en RAM, les fragments sont traités et écrits sur disque au fil de l'eau.

---

## 6. Configuration Variables & Hyperparameters

| **Variable** | **Type** | **Valeur par défaut** | **Description** |
|---|---|---:|---|
| `CHUNK_SIZE_CONFIG_A` | `int` | `300` | Taille cible des fragments pour la configuration fine (en caractères). |
| `CHUNK_OVERLAP_CONFIG_A` | `int` | `50` | Chevauchement entre fragments successifs (Configuration A). |
| `CHUNK_SIZE_CONFIG_B` | `int` | `1000` | Taille cible des fragments pour la configuration large (en caractères). |
| `CHUNK_OVERLAP_CONFIG_B` | `int` | `150` | Chevauchement entre fragments successifs (Configuration B). |
| `SEPARATORS` | `List[str]` | `["\n\n", "\n", " ", ""]` | Ordre de priorité des séparateurs de texte pour LangChain. |
| `MIN_CHUNK_LENGTH` | `int` | `10` | Longueur minimale d'un fragment valide pour filtrer le bruit. |

---

## 7. Cost & Resource Tracking Strategy

- **CPU & Execution Time :**  
  Mesure du temps d'exécution (en millisecondes) par fragment et par document pour évaluer l'impact sur la chaîne globale.

- **Memory Footprint :**  
  Suivi de l'empreinte mémoire maximale (*Peak Memory*) pour garantir que le processus s'exécute dans des conteneurs légers (< 512 Mo de RAM).

- **Token Estimation (Projection Cloud / LLM) :**  
  Calcul du ratio moyen `caractères / 4` pour estimer le coût futur d'embedding et de requêtage LLM.

---

## 8. Phased Implementation Roadmap

### Phase 1 : Conception du Modèle de Données & Engine Base

`[██████████]` **100%**

- Définition du schéma Pydantic `ChunkModel`.
- Implémentation du sous-module de découpage basé sur LangChain `RecursiveCharacterTextSplitter`.

### Phase 2 : Gestion des Métadonnées & Multi-configurations

`[██████████]` **100%**

- Intégration du module d'injection des métadonnées (page, provenance, typologie).
- Implémentation du comparateur de configurations (Config A vs Config B).

### Phase 3 : Benchmarking, Tests & Livrables

`[██████████]` **100%**

- Exécution des tests unitaires (`pytest`).
- Rédaction du rapport comparatif et préparation de la démonstration.

---

## 9. Validation Test Protocol

### Test Case 1 : Découpage d'un document TXT plat (Config A)

- **Entrée :** Document texte brut de 1 000 caractères sans notion de page.

- **Résultat attendu :**
  - ~4 à 5 fragments générés.
  - `page_number` égal à `None`.
  - Présence exacte du chevauchement de 50 caractères entre les fragments N et N+1.

---

### Test Case 2 : Découpage du rapport `HPS.pdf` (Config B)

- **Entrée :** Fichier `HPS.pdf` (8 040 caractères, 6 pages).

- **Résultat attendu :**
  - Les métadonnées conservent le numéro de page d'origine pour chaque chunk.
  - Aucun fragment ne dépasse 1 000 caractères.
  - Tous les `chunk_id` sont des UUIDs valides et uniques.

---

### Test Case 3 : Gestion d'un document vide (`pdf_vide.pdf`)

- **Entrée :** Fichier de 0 caractère texte.

- **Résultat attendu :**
  - 0 fragment généré.
  - Aucune exception ou plantage du pipeline.

---

## 10. Summary

Cette architecture de découpage et de structuration de métadonnées transforme les données brutes extraites par `DocumentExtractor` en structures prêtes pour l'indexation dans un système RAG.

En combinant la puissance de découpage sémantique de LangChain et la rigueur de typage de Pydantic, le système assure une traçabilité complète de l'information :

- Pagination
- Document source
- Typologie du document
- Volumétrie
- Identifiant unique du chunk

L'expérimentation guidée entre la **Configuration A** et la **Configuration B** permettra d'évaluer le compromis idéal entre **précision de recherche** et **préservation du contexte métier**.

---

### Architecture finale

```text
                         ┌──────────────────────────────┐
                         │  DocumentExtractor Output    │
                         │          JSON                │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     Text Splitter Layer      │
                         │ RecursiveCharacterTextSplitter│
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │  Metadata Injection Engine   │
                         │ UUID + Page + Source + Size  │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │     Pydantic Validation      │
                         │       DocumentChunk          │
                         └──────────────┬───────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────────┐
                         │    Vector Storage Payload    │
                         │       Ready for RAG          │
                         └──────────────────────────────┘
```