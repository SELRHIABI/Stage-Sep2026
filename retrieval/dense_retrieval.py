import os
import json
from typing import List
import chromadb
from sentence_transformers import SentenceTransformer
from rich.console import Console

from retrieval.schemas import ChunkInput, SearchResult

# Hyperparamètres par défaut
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
COLLECTION_NAME = "rag_chunks"
CHROMA_DB_PATH = "./chroma_db"
TOP_K_RESULTS = 3
BATCH_SIZE = 32

console = Console()


class DenseRetrievalPipeline:
    def __init__(
        self,
        db_path: str = CHROMA_DB_PATH,
        collection_name: str = COLLECTION_NAME,
    ):
        console.print(
            f"[bold blue]Init:[/bold blue] Chargement du modèle [green]{EMBEDDING_MODEL_NAME}[/green]..."
        )
        self.embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

        console.print(
            f"[bold blue]Init:[/bold blue] Connexion ChromaDB ([yellow]{db_path}[/yellow])..."
        )
        self.chroma_client = chromadb.PersistentClient(path=db_path)

        # Re-création propre de la collection pour garantir l'idempotence
        try:
            self.chroma_client.delete_collection(name=collection_name)
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def load_and_validate_chunks(
        self, json_file_path: str
    ) -> List[ChunkInput]:
        """Stage 1 : Chargement et validation Pydantic des chunks."""
        if not os.path.exists(json_file_path):
            console.print(
                f"[bold red]Erreur :[/bold red] Fichier {json_file_path} introuvable."
            )
            return []

        with open(json_file_path, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        validated_chunks = []
        for idx, item in enumerate(raw_data):
            meta = item.get("metadata", {})
            if "source_document" not in meta:
                meta["source_document"] = "summary_report.pdf"
            if "page_number" not in meta:
                meta["page_number"] = 1

            # Récupération sécurisée de l'ID (id ou chunk_id ou index généré)
            chunk_id = str(
                item.get(
                    "id", item.get("chunk_id", meta.get("chunk_id", f"chunk_{idx}"))
                )
            )
            content = item.get("content", item.get("text", ""))

            chunk = ChunkInput(id=chunk_id, content=content, metadata=meta)
            validated_chunks.append(chunk)

        console.print(
            f"[bold green]Stage 1 OK :[/bold green] {len(validated_chunks)} chunks validés."
        )
        return validated_chunks

    def ingest_chunks(self, chunks: List[ChunkInput]):
        """Stage 2 : Vectorisation par lots et stockage dans ChromaDB."""
        if not chunks:
            return

        documents = [c.content for c in chunks]
        ids = [c.id for c in chunks]
        metadatas = [c.metadata for c in chunks]

        embeddings = self.embedding_model.encode(
            documents,
            batch_size=BATCH_SIZE,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()

        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        console.print(
            f"[bold green]Stage 2 OK :[/bold green] {len(chunks)} chunks indexés dans ChromaDB."
        )

    def search(
        self, query: str, top_k: int = TOP_K_RESULTS
    ) -> List[SearchResult]:
        """Stage 3 : Vectorisation de la requête et recherche K-NN."""
        query_vector = self.embedding_model.encode(
            [query], convert_to_numpy=True
        ).tolist()

        raw_results = self.collection.query(
            query_embeddings=query_vector,
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        results = []
        if raw_results and raw_results["ids"]:
            ids = raw_results["ids"][0]
            docs = raw_results["documents"][0]
            metas = raw_results["metadatas"][0]
            distances = raw_results["distances"][0]

            for i in range(len(ids)):
                # Normalisation du score de similarité cosinus : 1 - distance
                similarity_score = max(0.0, min(1.0, 1.0 - distances[i]))
                results.append(
                    SearchResult(
                        rank=i + 1,
                        chunk_id=ids[i],
                        content=docs[i],
                        similarity_score=round(similarity_score, 4),
                        metadata=metas[i],
                    )
                )

        return results