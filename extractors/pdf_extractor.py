import os
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from extractors.base import BaseExtractor
from models import ExtractionReport, ExtractionStatus, PageMetadata
from config import PREVIEW_CHAR_LIMIT

class PDFExtractor(BaseExtractor):
    def extract(self, file_path: str) -> ExtractionReport:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        try:
            reader = PdfReader(file_path)
            
            # Gestion des fichiers PDF chiffrés / protégés
            if reader.is_encrypted:
                try:
                    reader.decrypt("")
                except Exception:
                    return ExtractionReport(
                        file_path=file_path,
                        file_name=file_name,
                        file_size_bytes=file_size,
                        extension=".pdf",
                        status=ExtractionStatus.FAILED,
                        error_message="PDF protégé par un mot de passe non vide."
                    )

            extracted_text_list = []
            pages_detail = []
            
            # Parcours page par page
            for index, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                extracted_text_list.append(page_text)
                
                pages_detail.append(
                    PageMetadata(
                        page_number=index,
                        char_count=len(page_text),
                        preview=page_text[:PREVIEW_CHAR_LIMIT]
                    )
                )

            full_text = "\n".join(extracted_text_list)
            total_chars = len(full_text)
            preview = full_text[:PREVIEW_CHAR_LIMIT]

            return ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=".pdf",
                status=ExtractionStatus.SUCCESS,
                text=full_text,
                preview=preview,
                total_chars=total_chars,
                pages_count=len(reader.pages),
                pages_detail=pages_detail,
                metadata={"pdf_producer": reader.metadata.producer if reader.metadata else None}
            )

        except PdfReadError as e:
            return ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=".pdf",
                status=ExtractionStatus.FAILED,
                error_message=f"Fichier PDF corrompu ou illisible : {str(e)}"
            )
        except Exception as e:
            return ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=".pdf",
                status=ExtractionStatus.FAILED,
                error_message=f"Erreur d'extraction PDF : {str(e)}"
            )