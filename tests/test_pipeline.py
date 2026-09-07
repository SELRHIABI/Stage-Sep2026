import os
import pytest
from pipeline import DocumentPipeline
from models import ExtractionStatus

@pytest.fixture
def pipeline():
    return DocumentPipeline()

@pytest.fixture
def tmp_test_files(tmp_path):
    # Fichier TXT valide
    valid_txt = tmp_path / "valid.txt"
    valid_txt.write_text("Ceci est un document valide avec du texte propre.", encoding="utf-8")

    # Fichier vide
    empty_txt = tmp_path / "empty.txt"
    empty_txt.write_text("", encoding="utf-8")

    # Fichier PDF corrompu
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_text("Not a real PDF file header", encoding="utf-8")

    return {
        "valid": str(valid_txt),
        "empty": str(empty_txt),
        "corrupt": str(corrupt_pdf),
        "nonexistent": str(tmp_path / "missing.txt")
    }

def test_valid_txt_extraction(pipeline, tmp_test_files):
    report = pipeline.process_document(tmp_test_files["valid"])
    assert report.status == ExtractionStatus.SUCCESS
    assert report.total_chars > 0
    assert report.quality_score > 80.0

def test_empty_file_rejection(pipeline, tmp_test_files):
    report = pipeline.process_document(tmp_test_files["empty"])
    assert report.status == ExtractionStatus.REJECTED
    assert "0 octet" in report.error_message

def test_nonexistent_file_rejection(pipeline, tmp_test_files):
    report = pipeline.process_document(tmp_test_files["nonexistent"])
    assert report.status == ExtractionStatus.REJECTED
    assert "introuvable" in report.error_message

def test_corrupted_pdf_handling(pipeline, tmp_test_files):
    report = pipeline.process_document(tmp_test_files["corrupt"])
    assert report.status == ExtractionStatus.FAILED
    assert report.error_message is not None