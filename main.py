import argparse
import json
import os
from pipeline import DocumentPipeline
from retrieval.chunking import chunk_document
from retrieval.dense_retrieval import ingest_chunks
# Import de ta vraie recherche hybride
from retrieval.hybrid_retrieval import hybrid_search as true_hybrid_search

# --- FONCTIONS EXPOSÉES POUR L'INTERFACE (ui/app.py) ---

def index_pdf_file(file_path):
    """Traite un fichier PDF unique, génère son rapport JSON,
    le découpe (chunking) et l'indexe dans la base vectorielle.
    """
    try:
        pipeline = DocumentPipeline()
        reports = pipeline.process_batch([file_path])

        output_dir = "./summary"
        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_report.json")

        reports_dict = [report.model_dump() for report in reports]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(reports_dict, f, indent=4, ensure_ascii=False)

        chunks = chunk_document(output_path)
        if chunks:
            ingest_chunks(chunks)
            return True
    except Exception as e:
        print(f"[ERREUR] Échec de l'indexation de {file_path} : {e}")
    return False

def hybrid_search(query, current_files, n_results=3):
    """Appelle ta vraie fonction hybrid_search pour chaque fichier attaché à la discussion active."""
    all_results = []
    
    if not current_files:
        return all_results

    for file_name in current_files:
        try:
            # Appel de ta fonction définie dans hybrid_retrieval.py
            results = true_hybrid_search(query=query, target_file=file_name, n_results=n_results)
            for res in results:
                # Assure-toi que le nom du fichier est bien présent dans le dictionnaire de retour
                res["file_name"] = file_name
                # Normalise la clé du texte si nécessaire ("content" vs "text")
                if "text" in res and "content" not in res:
                    res["content"] = res["text"]
                all_results.append(res)
        except Exception as e:
            print(f"[ERREUR] Recherche hybride pour {file_name} : {e}")
            
    # Tri par score décroissant pour garder les meilleurs fragments
    all_results = sorted(all_results, key=lambda x: x.get("score", 0), reverse=True)
    return all_results

def generate_rag_response(query, retrieved_fragments):
    """Génère la réponse finale via Ollama (DeepSeek-R1) en utilisant les fragments récupérés."""
    context = "\n\n".join([
        f"Page {f.get('page', 1)} ({f.get('file_name', 'Doc')}): {f.get('content', '')}" 
        for f in retrieved_fragments
    ])
    
    import ollama
    prompt = f"Tu es un assistant expert. Réponds à la question en te basant STRICTEMENT et UNIQUEMENT sur le contexte fourni ci-dessous. Si la réponse n'y est pas, dis-le clairement.\n\nContexte :\n{context}\n\nQuestion : {query}"
    
    response = ollama.chat(
        model="deepseek-r1",
        messages=[{"role": "user", "content": prompt}]
    )
    return response['message']['content']


# --- MODE CLI (Ligne de commande d'origine) ---
def main():
    default_summary_dir = "./summary"
    default_output_path = os.path.join(default_summary_dir, "summary_report.json")

    parser = argparse.ArgumentParser(description="DocumentExtractor CLI")
    parser.add_argument("path", help="Chemin vers un fichier ou un dossier de documents")
    parser.add_argument("--output", default=default_output_path, help="Chemin du fichier JSON de sortie")
    args = parser.parse_args()

    files_to_process = []
    if os.path.isdir(args.path):
        for root, _, files in os.walk(args.path):
            for file in files:
                files_to_process.append(os.path.join(root, file))
    elif os.path.isfile(args.path):
        files_to_process.append(args.path)
    else:
        print(f"[ERREUR] Chemin introuvable : {args.path}")
        return

    print(f"=== Traitement de {len(files_to_process)} fichier(s) ===\n")

    pipeline = DocumentPipeline()
    reports = pipeline.process_batch(files_to_process)

    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    reports_dict = [report.model_dump() for report in reports]
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(reports_dict, f, indent=4, ensure_ascii=False)

    print(f"\n[INFO] Rapport exporté dans {args.output}")

    print("\n=== Lancement du Chunking et de l'Indexation Vectorielle ===")
    try:
        chunks = chunk_document(args.output)
        print(f"[INFO] {len(chunks)} chunks générés avec succès.")
        ingest_chunks(chunks)
        print("[INFO] Indexation dans ChromaDB terminée avec succès !")
    except Exception as e:
        print(f"[ERREUR] Échec lors du traitement RAG : {e}")

if __name__ == "__main__":
    main()