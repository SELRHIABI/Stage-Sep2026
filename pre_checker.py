import os
from typing import Tuple, Optional
from config import MAX_FILE_SIZE_MB, SUPPORTED_EXTENSIONS
from models import ExtractionReport, ExtractionStatus

class PreChecker:
    @staticmethod
    def validate(file_path: str) -> Tuple[bool, Optional[ExtractionReport]]:
        file_name = os.path.basename(file_path)
        _, ext = os.path.splitext(file_name)
        ext = ext.lower()

        # 1. Vérification de l'existence
        if not os.path.exists(file_path):
            report = ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=0,
                extension=ext,
                status=ExtractionStatus.REJECTED,
                error_message="Fichier introuvable sur le système disque."
            )
            return False, report

        file_size = os.path.getsize(file_path)

        # 2. Vérification fichier vide (0 octet)
        if file_size == 0:
            report = ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=0,
                extension=ext,
                status=ExtractionStatus.REJECTED,
                error_message="Fichier vide (0 octet)."
            )
            return False, report

        # 3. Vérification de la taille maximale
        max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
        if file_size > max_bytes:
            report = ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=ext,
                status=ExtractionStatus.REJECTED,
                error_message=f"Taille du fichier ({file_size / (1024*1024):.2f} MB) dépasse la limite autorisée ({MAX_FILE_SIZE_MB} MB)."
            )
            return False, report

        # 4. Vérification de l'extension
        if ext not in SUPPORTED_EXTENSIONS:
            report = ExtractionReport(
                file_path=file_path,
                file_name=file_name,
                file_size_bytes=file_size,
                extension=ext,
                status=ExtractionStatus.REJECTED,
                error_message=f"Extension '{ext}' non supportée. Formats acceptés : {SUPPORTED_EXTENSIONS}"
            )
            return False, report

        return True, None