import chromadb
from sentence_transformers import SentenceTransformer

# Nom du modèle d'embedding local
MODEL_NAME = "all-MiniLM-L6-v2"


def get_chroma_collection(collection_name="rag_chunks"):
    """Initialise le client ChromaDB persistant et récupère ou crée la collection."""
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name=collection_name)
    return collection


def ingest_chunks(chunks):
    """Vectorise les chunks de texte et les enregistre dans ChromaDB."""
    if not chunks:
        print("[AVERTISSEMENT] Aucun chunk à ingérer.")
        return

    collection = get_chroma_collection()
    
    # Nettoie les anciens chunks pour éviter les doublons de manière compatible avec ChromaDB
    existing_data = collection.get()
    if existing_data and existing_data["ids"]:
        collection.delete(ids=existing_data["ids"])
        print("[INFO] Ancienne base nettoyée avec succès.")

    model = SentenceTransformer(MODEL_NAME)

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    print(f"[INFO] Génération des embeddings pour {len(texts)} chunks...")
    embeddings = model.encode(texts).tolist()

    # Ajout ou mise à jour dans ChromaDB
    collection.upsert(
        ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
    )
    print(
        f"[INFO] {len(chunks)} chunks indexés avec succès dans la base ChromaDB."
    )


def search(query_text, n_results=3):
    """Recherche les chunks les plus proches sémantiquement d'une question."""
    collection = get_chroma_collection()
    model = SentenceTransformer(MODEL_NAME)

    query_embedding = model.encode([query_text]).tolist()

    results = collection.query(query_embeddings=query_embedding, n_results=n_results)
    return results