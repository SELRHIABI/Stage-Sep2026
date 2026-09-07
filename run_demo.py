import json
from pathlib import Path
from chunking.chunking_pipeline import ChunkingEngine, CONFIG_A, CONFIG_B

# 1. Chargement du rapport généré par main.py
report_path = Path("summary/summary_report.json")

if not report_path.exists():
    print("[ERREUR] Le fichier summary/summary_report.json n'existe pas. Lance d'abord main.py !")
    exit(1)

with open(report_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Récupération du premier document
sample_extraction = data[0] if isinstance(data, list) else data

# 2. Adaptation automatique à la structure du DocumentExtractor
filename = sample_extraction.get("filename") or sample_extraction.get("file_name") or "HPS.pdf"

if "pages" not in sample_extraction or not sample_extraction["pages"]:
    full_text = sample_extraction.get("text") or sample_extraction.get("extracted_text") or ""
    sample_extraction["pages"] = [{"page_number": 1, "text": full_text}]

for page in sample_extraction.get("pages", []):
    if "text" not in page and "content" in page:
        page["text"] = page["content"]

total_text_length = sum(len(page.get("text", "")) for page in sample_extraction.get("pages", []))
if total_text_length == 0 and "text" in sample_extraction:
    total_text_length = len(sample_extraction["text"])

sample_extraction["filename"] = filename

# 3. Exécution des deux moteurs de Chunking
engine_a = ChunkingEngine(CONFIG_A["chunk_size"], CONFIG_A["chunk_overlap"])
chunks_a = engine_a.process_document(sample_extraction)

engine_b = ChunkingEngine(CONFIG_B["chunk_size"], CONFIG_B["chunk_overlap"])
chunks_b = engine_b.process_document(sample_extraction)

# 4. Affichage du Benchmark général
print("=== RÉSULTATS DU BENCHMARK ===")
print(f"Fichier source : {filename}")
print(f"Taille originale du texte : {total_text_length} caractères")
print(f"Nombre de chunks générés (Config A - 300/50) : {len(chunks_a)}")
print(f"Nombre de chunks générés (Config B - 1000/150) : {len(chunks_b)}\n")

# 5. Affichage des 3 premiers chunks de la CONFIG A
print("==================================================")
print("=== EXEMPLES DE CHUNKS (Config A - 300/50) ===")
print("==================================================")
for i, chunk in enumerate(chunks_a[:3], 1):
    print(f"\n--- Chunk {i}/{len(chunks_a)} ---")
    print(json.dumps(chunk.model_dump(), indent=2, ensure_ascii=False))

# 6. Affichage des 3 premiers chunks de la CONFIG B
print("\n==================================================")
print("=== EXEMPLES DE CHUNKS (Config B - 1000/150) ===")
print("==================================================")
for i, chunk in enumerate(chunks_b[:3], 1):
    print(f"\n--- Chunk {i}/{len(chunks_b)} ---")
    print(json.dumps(chunk.model_dump(), indent=2, ensure_ascii=False))