import ollama
import sys

def generate_rag_response(query: str, retrieved_fragments: list) -> str:
    """
    Génère une réponse basée sur les fragments validés avec affichage en streaming
    et citation rigoureuse du fichier source.
    """
    if not retrieved_fragments:
        return "🛡️ Je suis désolé, mais je ne trouve pas d'information pertinente dans les documents pour répondre à votre question."

    # 1. Construction du contexte avec le nom exact du fichier récupéré
    context_blocks = []
    for frag in retrieved_fragments:
        file_name = frag.get('file_name', 'test2.pdf')
        source_info = f"[Fichier: {file_name} | Page {frag['page']} | Moteur: {frag['source']}]"
        context_blocks.append(f"{source_info}\n{frag['text']}")
    
    context_text = "\n\n---\n\n".join(context_blocks)

    # 2. Prompt strict exigeant le format exact du lien avec le vrai nom de fichier
    system_prompt = (
        "Vous êtes un assistant documentaire rigoureux. "
        "Vous devez répondre à la question de l'utilisateur **uniquement** en vous basant sur le contexte fourni. "
        "Vous devez répondre en vous basant uniquement sur le contexte. Vous êtes autorisé à synthétiser, expliquer et relier les concepts abordés dans les documents pour répondre à la question de l'utilisateur, sans jamais inventer de faits externes."
        "À la fin de votre réponse, vous devez obligatoirement citer la source sous ce format exact de lien Markdown : "
        "📄 Source : [NomExactDuFichier.pdf (Page X)](NomExactDuFichier.pdf), "
        "en remplaçant 'NomExactDuFichier.pdf' et 'X' par les vraies valeurs présentes dans le contexte."
    )

    user_prompt = f"Contexte document :\n{context_text}\n\nQuestion : {query}"

    print("🤖 (Génération en cours avec DeepSeek-R1...)\n")
    
    try:
        stream = ollama.chat(
            model='deepseek-r1',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            options={'temperature': 0.0},
            stream=True
        )

        full_response = ""
        for chunk in stream:
            content = chunk['message']['content']
            print(content, end='', flush=True)
            full_response += content
            
        print("\n")
        return full_response
    
    except Exception as e:
        return f"⚠️ Erreur de communication avec le serveur Ollama : {str(e)}"