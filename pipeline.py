import os
from typing import Dict, Type, List
from concurrent.futures import ProcessPoolExecutor

from models import ExtractionReport, ExtractionStatus
from config import MAX_WORKERS
from pre_checker import PreChecker
from quality_checker import QualityChecker
from extractors.base import BaseExtractor
from extractors.txt_extractor import TXTExtractor
from extractors.pdf_extractor import PDFExtractor


def _worker_process_file(file_path: str) -> ExtractionReport:
    """
    Fonction globale au niveau du module nécessaire pour la sérialisation 
    (pickling) lors du traitement multi-processus avec ProcessPoolExecutor.
    """
    pipeline = DocumentPipeline()
    return pipeline.process_document(file_path)


class DocumentPipeline:
    def __init__(self):
        # Enregistrement des stratégies d'extraction par extension
        self._extractors: Dict[str, Type[BaseExtractor]] = {
            ".txt": TXTExtractor,
            ".pdf": PDFExtractor
        }

    def process_document(self, file_path: str) -> ExtractionReport:
        """
        Exécute le pipeline d'ingestion complet pour un seul fichier :
        Stage 1 (Pre-Check) -> Stage 2 (Parsing) -> Stage 3 (Quality Scoring)
        """
        try:
            # Stage 1: Pre-Checker & Validation physique
            is_valid, error_report = PreChecker.validate(file_path)
            if not is_valid and error_report:
                return error_report

            file_name = os.path.basename(file_path)
            _, ext = os.path.splitext(file_name)
            ext = ext.lower()

            # Stage 2: Routage de format & Extraction via Strategy
            extractor_class = self._extractors.get(ext)
            if not extractor_class:
                return ExtractionReport(
                    file_path=file_path,
                    file_name=file_name,
                    file_size_bytes=os.path.getsize(file_path) if os.path.exists(file_path) else 0,
                    extension=ext,
                    status=ExtractionStatus.REJECTED,
                    error_message=f"Aucun extracteur configuré pour l'extension '{ext}'."
                )

            extractor = extractor_class()
            report = extractor.extract(file_path)

            # Stage 3: Quality Scoring Engine
            if report.status == ExtractionStatus.SUCCESS:
                report = QualityChecker.evaluate(report)

            return report

        except Exception as e:
            # Isolation Zero-Crash : Capture de toute exception inattendue au niveau du pipeline
            file_name = os.path.basename(file_path) if file_path else "unknown"
            _, ext = os.path.splitext(file_name) if file_path else ("", "")
            return ExtractionReport(
                file_path=file_path or "",
                file_name=file_name,
                file_size_bytes=os.path.getsize(file_path) if file_path and os.path.exists(file_path) else 0,
                extension=ext.lower(),
                status=ExtractionStatus.FAILED,
                error_message=f"Erreur inattendue au niveau du pipeline : {str(e)}"
            )

    def process_batch(self, file_paths: List[str], max_workers: int = MAX_WORKERS) -> List[ExtractionReport]:
        """
        Traite une liste de fichiers en parallèle en utilisant ProcessPoolExecutor
        pour contourner le GIL Python lors des tâches dépendantes du CPU.
        """
        if not file_paths:
            return []

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            reports = list(executor.map(_worker_process_file, file_paths))
            
        return reports