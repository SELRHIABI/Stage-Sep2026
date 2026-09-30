# Guide de Stratégie Technique : Interface RAG Locale & Gestion des Sessions (Streamlit)

Ce document formalise l'architecture logicielle mise à jour, intégrant la gestion multi-sessions de type *Gemini* dans la barre latérale, ainsi que le découplage strict entre la couche de présentation (UI) et le moteur de calcul (Core RAG Engine).

---

## 1. Vision d'Architecture & Organisation des Flux

L'interface Streamlit joue le rôle de contrôleur de présentation. Elle gère l'état conversationnel multi-threads et délègue l'intégralité du traitement lourd au backend RAG local.

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    Interface Utilisateur (Streamlit)                    │
│  - Sidebar Multi-Sessions (Création, Sélection, Historique des chats)   │
│  - Paramètres Dynamiques (Seuils Dense/BM25, Top-K, Upload PDF)        │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (Appels synchrones / asynchrones)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                       Moteur RAG Core (Python)                          │
│  - Ingestion & Chunking (DocumentExtractor)                             │
│  - Recherche Hybride (ChromaDB + BM25 + Double Seuil)                   │
│  - Génération LLM (Ollama / DeepSeek-R1-1.5B + Chain of Thought)        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Spécifications Fonctionnelles de l'Interface (UI/UX)

* **Sidebar Dynamique (Style Gemini) :**
  * **Bouton d'action rapide :** Création instantanée d'une nouvelle session de discussion.
  * **Liste des discussions :** Historique cliquable permettant de basculer d'un contexte conversationnel à un autre sans perte de données.
  * **Panneau de configuration du RAG :** Zone de téléversement de documents PDF et curseurs de réglage des seuils de recherche hybride (Dense et BM25).
* **Zone de Discussion Principale (Chat View) :**
  * Affichage de l'historique des messages propres à la session active (`st.chat_message`).
  * Indicateur visuel de chargement lors de la phase de recherche et de raisonnement du modèle.
  * Rendu strict des citations sous forme de liens Markdown cliquables (`[Nom du fichier (Page X)](...)`) pour assurer la traçabilité et respecter la politique zéro-hallucination.

---

## 3. Architecture des Fichiers du Projet

```text
DocumentExtractor/
│
├── core/                        # Cœur du moteur RAG
│   ├── hybrid_search.py         # ChromaDB + BM25 + Double seuil
│   ├── generator.py             # Intégration Ollama / DeepSeek-R1
│   └── ingestion.py             # Traitement des PDF & Chunking
│
├── docs/
│   └── interface_strategy_guide.md # Ce document
│
├── tests/                       # Scripts de tests unitaires
│   ├── test_dense_retrieval.py
│   └── test_word_retrieval.py
│
├── ui/                          # Couche Interface Graphique
│   └── app.py                   # Application Streamlit principale (Multi-sessions)
│
├── requirements.txt             # Dépendances (incluant streamlit)
└── README.md
```

---

## 4. Stratégie de Gestion des États (`st.session_state`)

Pour éviter la réinitialisation des données à chaque interaction induite par le cycle de vie de Streamlit, l'état global repose sur deux piliers :
1. **`st.session_state.sessions`** : Dictionnaire associant le nom de chaque conversation à sa liste de messages (`{"Discussion 1": [{"role": "user", "content": "..."}, ...]}`).
2. **`st.session_state.current_session`** : Chaîne de caractères identifiant la session active affichée à l'écran.
3. **Mise en cache des modèles** : Utilisation de `@st.cache_resource` pour charger ChromaDB et Ollama une seule fois au démarrage, garantissant des performances fluides.

---

## 5. Plan de Réalisation et Prochaines Étapes

1. **Étape 1 :** Finalisation et validation de la structure du fichier `ui/app.py` intégrant la sidebar de type Gemini.
2. **Étape 2 :** Connexion des fonctions d'ingestion de PDF via la sidebar vers le module `DocumentExtractor`.
3. **Étape 3 :** Branchement de la zone de chat sur le pipeline de recherche hybride et génération via DeepSeek-R1.
4. **Étape 4 :** Tests utilisateurs locaux de l'interface et validation du comportement anti-hallucination avec citations Markdown.