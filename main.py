import argparse
import json
import os
from pipeline import DocumentPipeline

# Import de tes modules RAG pour enchaîner le traitement automatiquement
from retrieval.chunking import chunk_document
from retrieval.dense_retrieval import ingest_chunks


def main():
  # Dossier par défaut pour les rapports
  default_summary_dir = "./summary"
  default_output_path = os.path.join(default_summary_dir, "summary_report.json")

  parser = argparse.ArgumentParser(description="DocumentExtractor CLI")
  parser.add_argument(
      "path", help="Chemin vers un fichier ou un dossier de documents"
  )
  parser.add_argument(
      "--output",
      default=default_output_path,
      help="Chemin du fichier JSON de sortie",
  )
  args = parser.parse_args()

  files_to_process = []

  # Si l'argument est un dossier, on prend tous les fichiers dedans
  if os.path.isdir(args.path):
    for root, _, files in os.walk(args.path):
      for file in files:
        files_to_process.append(os.path.join(root, file))
  # Si l'argument est un seul fichier
  elif os.path.isfile(args.path):
    files_to_process.append(args.path)
  else:
    print(f"[ERREUR] Chemin introuvable : {args.path}")
    return

  print(f"=== Traitement de {len(files_to_process)} fichier(s) ===\n")

  pipeline = DocumentPipeline()
  reports = pipeline.process_batch(files_to_process)

  for report in reports:
    print(f"[FICHIER]: {report.file_name}")
    print(f"[STATUT]: {report.status}")
    print(f"[QUALITÉ]: {report.quality_score}% ({report.quality_label})")
    print(f"[PAGES]: {report.pages_count}")
    if report.preview:
      print(f"[APERÇU]: {report.preview[:100]}...")
    if report.error_message:
      print(f"[ERREUR]: {report.error_message}")
    print("-" * 50)

  # Création du dossier 'summary' s'il n'existe pas encore
  output_dir = os.path.dirname(args.output)
  if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir, exist_ok=True)

  # Export JSON
  reports_dict = [report.model_dump() for report in reports]
  with open(args.output, "w", encoding="utf-8") as f:
    json.dump(reports_dict, f, indent=4, ensure_ascii=False)

  print(f"\n[INFO] Rapport exporté dans {args.output}")

  # === ENCHAÎNEMENT AUTOMATIQUE DU RAG ===
  print("\n=== Lancement du Chunking et de l'Indexation Vectorielle ===")
  try:
    # 1. Découpage du rapport généré en chunks
    chunks = chunk_document(args.output)
    print(f"[INFO] {len(chunks)} chunks générés avec succès.")

    # 2. Indexation des chunks dans ChromaDB via dense_retrieval
    ingest_chunks(chunks)
    print(
        "[INFO] Indexation dans ChromaDB terminée avec succès ! Prêt pour la"
        " visualisation."
    )
  except Exception as e:
    print(f"[ERREUR] Échec lors du traitement RAG (Chunking/Ingestion) : {e}")


if __name__ == "__main__":
  main()