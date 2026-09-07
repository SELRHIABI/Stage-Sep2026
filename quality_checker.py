from config import QUALITY_THRESHOLD_HIGH, QUALITY_THRESHOLD_LOW
from models import QualityLabel, ExtractionReport

class QualityChecker:
    @staticmethod
    def evaluate(report: ExtractionReport) -> ExtractionReport:
        if report.status != "SUCCESS" or not report.text:
            report.quality_score = 0.0
            report.quality_label = QualityLabel.SUSPICIOUS_OR_SCAN
            return report

        total_chars = len(report.text)
        if total_chars == 0:
            report.quality_score = 0.0
            report.quality_label = QualityLabel.SUSPICIOUS_OR_SCAN
            return report

        # Compte des caractères alphanumériques et espaces
        valid_chars = sum(1 for c in report.text if c.isalnum() or c.isspace())
        score = round((valid_chars / total_chars) * 100, 2)
        report.quality_score = score

        # Classification
        if score >= QUALITY_THRESHOLD_HIGH:
            report.quality_label = QualityLabel.HIGH_QUALITY
        elif score >= QUALITY_THRESHOLD_LOW:
            report.quality_label = QualityLabel.MEDIUM_QUALITY
        else:
            report.quality_label = QualityLabel.SUSPICIOUS_OR_SCAN

        return report