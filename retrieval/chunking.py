import json
import os


def chunk_text_by_size(
    text: str,
    file_name: str,
    chunk_size: int = 800,
    overlap: int = 100,
):
    chunks = []
    start = 0
    text_len = len(text)
    idx = 0

    while start < text_len:
        end = start + chunk_size
        chunk_content = text[start:end]

        chunks.append(
            {
                "id": f"{file_name}_chunk_{idx}",
                "content": chunk_content.strip(),
                "metadata": {
                    "source_document": file_name,
                    "chunk_index": idx,
                },
            }
        )

        idx += 1
        start += chunk_size - overlap

    return chunks


def process_summary_file(input_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    all_chunks = []
    for doc in data:
        file_name = doc.get("file_name", "document.pdf")
        text = doc.get("text", "")
        doc_chunks = chunk_text_by_size(text, file_name)
        all_chunks.extend(doc_chunks)

    with open(input_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(
        f"[OK] Chunking par taille terminé : {len(all_chunks)} chunks générés."
    )


if __name__ == "__main__":
    process_summary_file("summary/summary_report.json")