import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ------------------------------------------------------------------------------
# 1. SCHÉMA PYDANTIC (Stage 3 & 4 du TAD)
# ------------------------------------------------------------------------------
class DocumentChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="UUID v4 unique du fragment")
    content: str = Field(..., description="Contenu textuel du fragment")
    source_document: str = Field(..., description="Nom du fichier original")
    document_type: str = Field(..., description="Extension ou type du document (ex: pdf, txt)")
    page_number: Optional[int] = Field(None, description="Numéro de page source si applicable")
    char_count: int = Field(..., description="Nombre de caractères dans le fragment")


# ------------------------------------------------------------------------------
# 2. CONFIGURATIONS HYPERPARAMÈTRES (Section 6 du TAD)
# ------------------------------------------------------------------------------
CONFIG_A = {
    "name": "Config A (Granularité Fine)",
    "chunk_size": 300,
    "chunk_overlap": 50
}

CONFIG_B = {
    "name": "Config B (Contextuelle Paragraphe)",
    "chunk_size": 1000,
    "chunk_overlap": 150
}

SEPARATORS = ["\n\n", "\n", " ", ""]


# ------------------------------------------------------------------------------
# 3. PIPELINE DE CHUNKING (Stage 2 & 3 du TAD)
# ------------------------------------------------------------------------------
class ChunkingEngine:
    def __init__(self, chunk_size: int, chunk_overlap: int):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=SEPARATORS
        )

    def process_document(self, extraction_report: Dict[str, Any]) -> List[DocumentChunk]:
        """
        Prend en entrée le rapport JSON de DocumentExtractor et retourne
        une liste d'objets DocumentChunk validés par Pydantic.
        """
        chunks: List[DocumentChunk] = []
        source_doc = extraction_report.get("filename", "unknown_doc")
        doc_type = extraction_report.get("extension", "txt").replace(".", "")
        pages_data = extraction_report.get("pages", [])

        # Si le document n'a pas de structure de pages (ex: fichier .txt plat)
        if not pages_data and "full_text" in extraction_report:
            raw_text = extraction_report["full_text"]
            text_splits = self.splitter.split_text(raw_text)
            for text in text_splits:
                chunks.append(
                    DocumentChunk(
                        content=text,
                        source_document=source_doc,
                        document_type=doc_type,
                        page_number=None,
                        char_count=len(text)
                    )
                )
            return chunks

        # Découpage page par page pour préserver le numéro de page
        for page_info in pages_data:
            page_num = page_info.get("page_number")
            page_text = page_info.get("text", "")
            
            if not page_text.strip():
                continue

            text_splits = self.splitter.split_text(page_text)
            for text in text_splits:
                chunks.append(
                    DocumentChunk(
                        content=text,
                        source_document=source_doc,
                        document_type=doc_type,
                        page_number=page_num,
                        char_count=len(text)
                    )
                )

        return chunks