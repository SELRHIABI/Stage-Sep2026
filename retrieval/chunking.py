import json

def chunk_document(json_path, chunk_size=600, overlap=100):
    """Lit le fichier JSON d'extraction et découpe le texte page par page en conservant les vrais numéros de page."""
    with open(json_path, "r", encoding="utf-8") as f:
        reports = json.load(f)

    # Si le JSON contient un seul rapport sous forme de dictionnaire au lieu d'une liste
    if isinstance(reports, dict):
        reports = [reports]

    all_chunks = []

    for report in reports:
        file_name = report.get("file_name", "document")
        pages_detail = report.get("pages_detail", [])

        # Cas de secours si le JSON n'a pas pages_detail mais un texte global
        if not pages_detail:
            text = (
                report.get("full_text", "") 
                or report.get("text", "") 
                or report.get("content", "") 
                or report.get("preview", "")
            )
            if not text:
                text = str(report)
            
            # Traitement par défaut si pas de pages_detail
            start = 0
            chunk_index = 0
            while start < len(text):
                end = start + chunk_size
                chunk_text = text[start:end]
                chunk_id = f"{file_name}_p1_chunk_{chunk_index}"
                all_chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "file_name": file_name,
                        "page_number": 1
                    }
                })
                start += chunk_size - overlap
                chunk_index += 1
            continue

        # Traitement itératif page par page (le cas idéal avec ton PDFExtractor)
        for page_info in pages_detail:
            page_number = page_info.get("page_number", 1)
            page_text = (
                page_info.get("text", "") 
                or page_info.get("preview", "")
            )

            if not page_text:
                continue

            start = 0
            chunk_index = 0
            while start < len(page_text):
                end = start + chunk_size
                chunk_text = page_text[start:end]

                chunk_id = f"{file_name}_p{page_number}_chunk_{chunk_index}"
                all_chunks.append({
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "file_name": file_name,
                        "page_number": page_number  # Numéro de page exact de la page courante
                    }
                })

                start += chunk_size - overlap
                chunk_index += 1

    return all_chunks