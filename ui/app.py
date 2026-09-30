import json
import os
import re
import streamlit as st

# Configuration de la page
st.set_page_config(
    page_title="DocumentExtractor - Assistant RAG", page_icon="🤖", layout="wide"
)

# Import des fonctions du backend (ajuste le chemin si nécessaire)
try:
  from main import generate_rag_response, hybrid_search, index_pdf_file
except ImportError:
  import sys

  sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
  from main import generate_rag_response, hybrid_search, index_pdf_file

HISTORY_FILE = "chat_history.json"


# --- GESTION DES SESSIONS ET PERSISTANCE ---
def load_sessions():
  if os.path.exists(HISTORY_FILE):
    try:
      with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        formatted = {}
        for k, v in data.items():
          # Rétrocompatibilité avec l'ancien format
          if isinstance(v, list):
            formatted[k] = {"messages": v, "files": []}
          else:
            formatted[k] = v
        return formatted
    except Exception:
      pass
  return {"Discussion principale": {"messages": [], "files": []}}


def save_sessions(sessions):
  with open(HISTORY_FILE, "w", encoding="utf-8") as f:
    json.dump(sessions, f, ensure_ascii=False, indent=2)


if "sessions" not in st.session_state:
  st.session_state.sessions = load_sessions()

if "current_session" not in st.session_state:
  st.session_state.current_session = (
      list(st.session_state.sessions.keys())[0]
      if st.session_state.sessions
      else "Discussion principale"
  )

current_session = st.session_state.current_session
if current_session not in st.session_state.sessions:
  st.session_state.sessions[current_session] = {"messages": [], "files": []}

session_data = st.session_state.sessions[current_session]
current_messages = session_data["messages"]
current_files = session_data["files"]


# --- SIDEBAR : GESTION DES DISCUSSIONS ---
with st.sidebar:
  st.title("💬 Discussions")

  if st.button("➕ Nouvelle discussion", use_container_width=True):
    new_name = f"Discussion {len(st.session_state.sessions) + 1}"
    st.session_state.sessions[new_name] = {"messages": [], "files": []}
    st.session_state.current_session = new_name
    save_sessions(st.session_state.sessions)
    st.rerun()

  st.divider()
  st.subheader("Historique")

  for session_name in list(st.session_state.sessions.keys()):
    col_btn, col_del = st.columns([0.8, 0.2])
    with col_btn:
      if st.button(
          session_name, key=f"btn_{session_name}", use_container_width=True
      ):
        st.session_state.current_session = session_name
        st.rerun()
    with col_del:
      if (
          st.button("🗑️", key=f"del_{session_name}")
          and len(st.session_state.sessions) > 1
      ):
        del st.session_state.sessions[session_name]
        if st.session_state.current_session == session_name:
          st.session_state.current_session = list(
              st.session_state.sessions.keys()
          )[0]
        save_sessions(st.session_state.sessions)
        st.rerun()


# --- INTERFACE PRINCIPALE ---
st.title(current_session)

# Affichage des fichiers attachés à la discussion en cours
if current_files:
  st.info(
      f"📂 **Documents associés à cette discussion :**"
      f" {', '.join(current_files)}"
  )
else:
  st.caption(
      "📂 Aucun document dans cette discussion. Utilisez le bouton '+' ci-dessous"
      " pour joindre vos PDF."
  )

# Affichage de l'historique des messages
for message in current_messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])

st.divider()

# --- BARRE DE SAISIE MODERNE (Inspirée de ton image) ---
# On utilise des colonnes pour mettre le bouton d'ajout de fichier (+) à gauche et la zone de texte à droite
col_file, col_input = st.columns([0.12, 0.88], vertical_alignment="bottom")

with col_file:
  uploaded_files = st.file_uploader(
      "➕",
      type="pdf",
      accept_multiple_files=True,
      key=f"uploader_{current_session}",
      label_visibility="collapsed",
  )

with col_input:
  prompt = st.chat_input("Ask Me... Let's discuss")

# --- TRAITEMENT DES FICHIERS UPLOADÉS ---
if uploaded_files:
  new_files_added = False
  for uploaded_file in uploaded_files:
    os.makedirs("data", exist_ok=True)
    file_path = os.path.join("data", uploaded_file.name)
    if not os.path.exists(file_path):
      with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # Indexation du fichier
    if index_pdf_file(file_path):
      if uploaded_file.name not in current_files:
        current_files.append(uploaded_file.name)
        new_files_added = True

  if new_files_added:
    save_sessions(st.session_state.sessions)
    st.success("📄 Fichiers indexés et liés à cette discussion avec succès !")
    st.rerun()

# --- TRAITEMENT DU MESSAGE UTILISATEUR ---
if prompt:
  current_messages.append({"role": "user", "content": prompt})

  # Détection des salutations avec regex
  cleaned_prompt = prompt.strip().lower()
  is_greeting = bool(
      re.match(
          r"^(he+l+o*|bo?njour+|salu+t+|coucou+|hi+|hey+|cc)+[\s!]*$",
          cleaned_prompt,
      )
  )

  if is_greeting:
    final_response = (
        "Bonjour ! Je suis prêt à discuter. Posez-moi vos questions sur les"
        " documents de cette discussion."
    )
    sources_str = "- Aucun document requis pour une salutation."
    retrieved_chunks = []
  else:
    with st.spinner("Analyse et génération de la réponse..."):
      try:
        # CORRECTION CRUCIALE : On passe 'current_files' et on retire les seuils obsolètes
        raw_chunks = hybrid_search(
            query=prompt, current_files=current_files, n_results=10
        )
        retrieved_chunks = raw_chunks[:5]
      except Exception as e:
        retrieved_chunks = []
        st.write(f"Erreur de recherche : {e}")

      try:
        response_text = generate_rag_response(
            query=prompt, retrieved_fragments=retrieved_chunks
        )
        if "<think>" in response_text and "</think>" in response_text:
          parts = response_text.split("</think>")
          final_response = parts[1].strip()
        else:
          final_response = response_text
      except Exception as e:
        final_response = f"⚠️ Erreur de génération : {str(e)}"

      sources_list = list(
          set(
              [
                  f"- `{chunk.get('file_name', 'Document')}` (Page {chunk.get('page', 1)})"
                  for chunk in retrieved_chunks
              ]
          )
      )
      sources_str = (
          "\n".join(sources_list)
          if sources_list
          else (
              "- Aucun document pertinent trouvé dans cette discussion pour"
              " cette question."
          )
      )

  final_saved_content = f"{final_response}\n\n### Sources :\n{sources_str}"
  current_messages.append(
      {"role": "assistant", "content": final_saved_content}
  )

  save_sessions(st.session_state.sessions)
  st.rerun()