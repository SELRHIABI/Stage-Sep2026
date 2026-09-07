from abc import ABC, abstractmethod
from models import ExtractionReport

class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, file_path: str) -> ExtractionReport:
        """
        Extrait le contenu et les métadonnées d'un fichier.
        Doit capturer ses propres erreurs internes sans faire crasher l'application.
        """
        pass