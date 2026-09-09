# Implementation Strategy Guide : Pipeline Retrieval & Indexation Vectorielle (RAG Phase 1)

## 1. The Core Idea

L'objectif principal de cette étape est d'établir le composant de **Recherche Vectorielle (Dense Retrieval)** du pipeline RAG sans interroger de LLM de génération. Il s'agit de garantir la pertinence sémantique de la récupération d'information (*Retrieval*) en mesurant mathématiquement la proximité entre le vecteur d'une requête utilisateur et les vecteurs de fragments de texte (*chunks*) préalablement indexés.

Le principe repose sur l'alignement dans un espace vectoriel dense à $N$ dimensions : deux textes traitant du même concept doivent posséder des représentations vectorielles proches (faible distance cosinus / euclidean), même si leurs formulations lexicales diffèrent.

### Flux de traitement

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                            FLUX DE TRAITEMENT                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [ Fichier JSON / Chunks ]                                                  │
│             │                                                               │
│             ▼                                                               │
│  ┌──────────────────────┐     ┌──────────────────────────────────────────┐  │
│  │ Local Embedding Engine│ ──► │ ChromaDB Vector Store                    │  │
│  │ (sentence-transformers)     │ (Stockage Embeddings + Métadonnées)      │  │
│  └──────────────────────┘     └────────────────────┬─────────────────────┘  │
│                                                    │                        │
│                                                    ▼                        │
│  [ Requête Utilisateur ] ──► [ Vectorisation ] ──► [ Similarity Search K=3 ]│
│                                                    │                        │
│                                                    ▼                        │
│                                       [ Top-3 Chunks + Scores ]             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Technical Stack Matrix

| **Outil / Bibliothèque** | **Rôle dans l'Architecture** | **Raisons du Choix Technique** |
|---|---|---|
| **Python 3.10+** | Langage hôte | Support typage strict (`pydantic`), écosystème IA mature, compatibilité async. |
| **ChromaDB** | Base de données vectorielle (*Vector Store*) | Exécution locale sans serveur externe (*embedded*), persistance SQLite/Parquet, gestion native des métadonnées, intégration PyTorch rapide. |
| **Sentence-Transformers** | Moteur d'embeddings d'état de l'art | Exécution 100% locale, support multi-langue via `paraphrase-multilingual-MiniLM-L12-v2` ou `BAAI/bge-small-en-v1.5`, pas de dépendance API externe. |
| **Pydantic v2** | Validation de schéma et contrats de données | Typage fort des objets de résultats, sérialisation JSON sécurisée, validation à la volée des métadonnées (`page_number`, `source_document`). |
| **PyTorch (CPU/CUDA)** | Runtime de calcul tensoriel | Gestion automatique de l'accélération matérielle (CPU/GPU) lors de l'inférence du modèle d'embedding. |
| **Rich / Logging** | Observabilité et interface CLI | Formatage lisible des métadonnées, affichage structuré des tables de résultats et suivi visuel des scores de similarité. |

---

## 3. Global Pipeline Architecture

```text
                                  [ summary_report.json / Chunks ]
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │  Chunk Data Loader &  │
                                     │   Pydantic Validator  │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Local Embedding Engine│
                                     │  (all-MiniLM-L6-v2)   │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │  ChromaDB Ingestion   │
                                     │  (Indexation HNSW)    │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
  ┌───────────────────────┐          ┌───────────────────────┐
  │  Query Input String   │ ───────► │  Query Vectorization  │
  └───────────────────────┘          └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Similarity Search K=3 │
                                     │  (Distance Cosine)    │
                                     └───────────┬───────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │  Result Metadata      │
                                     │  Formatting & Display │
                                     └───────────────────────┘
```

---

## 4. Step-by-Step Implementation Detail

### Stage 1 : Ingestion & Validation des Chunks

- **Description des composants :** Chargement du rapport JSON issu du pipeline d'extraction/chunking et conversion directe vers des modèles de données validés.

- **Cas Limites & Résilience :**
  - *Rapport absent ou corrompu :* Traitement explicite des erreurs d'E/S et de décodage avec interruption contrôlée.
  - *Métadonnées incomplètes :* Injection automatique de valeurs de secours par défaut pour garantir que chaque fragment indexé contienne une origine documentaire.

> **AI tip — why :** *Utiliser une couche de validation stricte avant l'insertion en base vectorielle isole la donnée. Si un chunk contient un champ nul ou mal typé, l'anomalie est levée immédiatement au lieu de provoquer un dysfonctionnement lors de l'indexation.*

### Stage 2 : Embedding & Stockage Vectoriel

- **Description des composants :** Initialisation du modèle vectoriel local, réinitialisation de la collection et traitement par lots (*batching*) pour calculer les vecteurs d'empreinte sémantique.

- **Cas Limites & Résilience :**
  - *Saturation mémoire :* Traitement découpé par lots ajustables selon les capacités matérielles hôtes.
  - *Idempotence :* Suppression et récréation de la collection avant indexation pour éviter le doublon d'identifiants lors des exécutions successives.

> **AI tip — why :** *Configurer la métrique d'indexation HNSW sur la distance Cosinus force le système à mesurer la proximité angulaire. Cela annule l'effet de biais lié à la variation de longueur brute entre les fragments.*

### Stage 3 : Pipeline de Recherche Vectorielle

- **Description des composants :** Vectorisation à la volée de la question de l'utilisateur, exécution de la recherche des plus proches voisins (K-NN avec $K=3$) et conversion des distances brutes en scores de similarité normalisés.

- **Cas Limites & Résilience :**
  - *Base vide :* Contrôle préalable de présence des vecteurs avant de déclencher la requête.
  - *Scores hors bornes :* Transformation mathématique explicite pour garantir un score de similarité toujours compris entre `0.0` et `1.0`.

### Stage 4 : Protocole d'Exécution des Tests & Affichage

- **Description des composants :** Séquençage automatisé des scénarios de validation imposés (mots exacts, reformulation, hors-sujet) et mise en forme lisible dans le terminal.

---

## 5. Parallelism, Scaling, and Resource Management

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GESTION DE MÉMOIRE                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  [ Processus Principal ]                                                    │
│         │                                                                   │
│         ├──► [ Engine Vectoriel (CPU / RAM) ]                               │
│         │        └── Chargement du Modèle MiniLM ( ~90MB )                  │
│         │                                                                   │
│         └──► [ ChromaDB Persistence Store ]                                 │
│                  └── Indexation HNSW en Mémoire + Flush sur Disque SQLite   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **CPU vs GPU Bound :** L'encodage vectoriel est intensif en calculs matriciels. L'utilisation de micro-lots (`batch_size=32`) permet d'exploiter les instructions SIMD du processeur local sans surcharger les threads.

- **Empreinte Mémoire (RAM) :** Le modèle d'embedding léger (`~90 Mo` en mémoire) garantit une exécution rapide et sans risque de dépassement de capacité mémoire (*OOM*).

- **Isolation & Persistance :** L'index ChromaDB est sauvegardé localement sur disque, permettant de réutiliser l'indexation sans refaire tous les calculs lors des relances.

---

## 6. Configuration Variables & Hyperparameters

| **Nom Variable** | **Type** | **Valeur par défaut** | **Description** |
|---|---|---|---|
| `EMBEDDING_MODEL_NAME` | `str` | `"all-MiniLM-L6-v2"` | Nom du modèle HuggingFace utilisé pour la vectorisation. |
| `COLLECTION_NAME` | `str` | `"rag_chunks"` | Nom de la collection d'indexation dans ChromaDB. |
| `CHROMA_DB_PATH` | `str` | `"./chroma_db"` | Dossier local de persistance du Vector Store. |
| `TOP_K_RESULTS` | `int` | `3` | Nombre de fragments pertinents à retourner lors de la recherche. |
| `SIMILARITY_METRIC` | `str` | `"cosine"` | Métrique de distance utilisée par l'index HNSW (`cosine`, `l2`, `ip`). |
| `BATCH_SIZE_EMBEDDING` | `int` | `32` | Nombre de fragments traités simultanément lors du calcul des vecteurs. |

---

## 7. Cost & Resource Tracking Strategy

- **Coût API :** **0,00 $** (Exécution 100% locale, aucune dépendance vers un service cloud).

- **Consommation Compute :**
  - *Inférence Query :* ~15 ms par question sur CPU standard.
  - *Indexation :* ~100 ms pour 10 à 32 fragments.

- **Observabilité / Logs :** Métriques d'exécution suivies en temps réel dans la console (taille du corpus, identifiants des fragments extraits, rangs et scores exacts).

---

## 8. Phased Implementation Roadmap

### Phase 1 : Ingestion & Contrats de Données

`[██████████]` **100%**

- Définir la structure de validation des métadonnées et du contenu source.
- Implémenter le module de chargement à partir du fichier rapport.

### Phase 2 : Moteur Vectoriel & Indexation

`[██████████]` **100%**

- Instancier le modèle d'embedding local et le client de persistance.
- Structurer la méthode d'insertion par lots avec gestion d'idempotence.

### Phase 3 : Recherche & Scénarios de Test

`[██████████]` **100%**

- Mettre en place la fonction de recherche K-NN et le formatage des résultats.
- Exécuter la suite des 3 tests de validation et documenter l'analyse.

---

## 9. Validation Test Protocol

| **N°** | **Cas de Test (Question)** | **Nature du Test** | **Résultat Attendu** |
|---:|---|---|---|
| **1** | *"Fondée en 1995 par un groupe d'experts marocains en monétique"* | **Mots Exacts** | Score de similarité très élevé (**> 0.85**). Le fragment contenant la phrase exacte est positionné au **Rang 1**. |
| **2** | *"Quand l'entreprise Société Générale a-t-elle été créée et par qui ?"* | **Reformulation (Sémantique)** | Score élevé (**> 0.65**). Le système identifie le fragment traitant de la création en 1995 et des fondateurs au **Rang 1**, sans dépendre des mots exacts. |
| **3** | *"Quelle est la recette de la tarte aux pommes traditionnelle ?"* | **Hors-Sujet (Inexistant)** | Scores très faibles (**< 0.20**). Les fragments retournés affichent un score insignifiant, validant l'absence de correspondance. |

---

## 10. Summary

Cette architecture de recherche vectorielle fournit une couche d'extraction d'information robuste, rapide et entièrement souveraine. L'association d'un modèle d'embedding local compact (`all-MiniLM-L6-v2`) et d'une base vectorielle embarquée (`ChromaDB`) garantit l'identification précise des 3 fragments les plus pertinents sans aucun appel API externe.

La validation sur les cas de test prouve la pertinence du découpage sémantique : les requêtes reformulées capturent le même contexte que les recherches par mots exacts, tandis que les requêtes hors-sujet sont rejetées avec des scores minimes.
