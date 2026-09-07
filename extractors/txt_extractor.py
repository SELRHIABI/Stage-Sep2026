import os
import chardet
from extractors.base import BaseExtractor
from models import ExtractionReport, ExtractionStatus, PageMetadata
from config import PREVIEW_CHAR_LIMIT, DEFAULT_TXT_ENCODING

class TXTExtractor(BaseExtractor):
    def extract(self, file_path: str) -> ExtractionReport:
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        
        try:
            # Détection automatique de l'encodage
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                
            detection = chardet.detect(raw_data)
            encoding = detection.get('encoding') or DEFAULT_TXT_ENCODING

            # Lecture sécurisée du texte
            text = raw_data.decode(encoding, errors='replace')
            total_chars = len(text)
            preview = text[:PREVIEW_CHAR_LIMIT]

            # Pour un fichier texte, on considère l'ensemble comme 1 seule page
            page_detail = PageMetadata(
                page_number=1,
                char_count=total_chars,
                preview=preview
            )

            return ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=".txt",
                status=ExtractionStatus.SUCCESS,
                text=text,
                preview=preview,
                total_chars=total_chars,
                pages_count=1,
                pages_detail=[page_detail],
                metadata={"detected_encoding": encoding, "confidence": detection.get('confidence')}
            )

        except Exception as e:
            return ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=".txt",
                status=ExtractionStatus.FAILED,
                error_message=f"Erreur d'extraction TXT: {str(e)}"
            )