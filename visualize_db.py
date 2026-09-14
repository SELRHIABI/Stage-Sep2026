import chromadb
import matplotlib.pyplot as plt
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
import numpy as np

# 1. Configuration et connexion
MODEL_NAME = "all-MiniLM-L6-v2"
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="rag_chunks")
model = SentenceTransformer(MODEL_NAME)

# 2. Définir une question de test pour la recherche
query_text = (
    "Quelles sont les différences entre un MLP et un CNN pour les images ?"
)
top_k = 3

# 3. Récupérer les données de la base ChromaDB
data = collection.get(include=["embeddings", "documents", "metadatas"])
embeddings = data["embeddings"]
metadatas = data["metadatas"]
ids = data["ids"]

if embeddings is None or len(embeddings) == 0:
  print("❌ La base de données est vide.")
  exit()

embeddings_np = np.array(embeddings)

# 4. Effectuer la recherche pour identifier les chunks les plus proches
results = collection.query(query_texts=[query_text], n_results=top_k)
retrieved_ids = results["ids"][0]  # Liste des IDs des chunks retournés

# 5. Vectoriser la question pour l'intégrer dans l'espace 2D
query_embedding = model.encode([query_text])

# Combiner les embeddings de la base et celui de la question pour la PCA
# (Cela garantit que tout le monde est projeté dans le même repère 2D)
combined_embeddings = np.vstack([embeddings_np, query_embedding])

# 6. Réduction de dimension (384D -> 2D)
pca = PCA(n_components=2)
coords_combined = pca.fit_transform(combined_embeddings)

# Séparer les coordonnées des chunks et celle de la question
coords_chunks = coords_combined[:-1]
coord_query = coords_combined[-1]

# 7. Création du graphique
plt.figure(figsize=(12, 8))

# Séparer les couleurs : chunks normaux vs chunks retrouvés
colors = []
sizes = []
for chunk_id in ids:
  if chunk_id in retrieved_ids:
    colors.append("limegreen")  # Chunks pertinents retrouvés
    sizes.append(150)
  else:
    colors.append("royalblue")  # Chunks standards
    sizes.append(80)

# Tracer les chunks
plt.scatter(
    coords_chunks[:, 0],
    coords_chunks[:, 1],
    c=colors,
    s=sizes,
    edgecolors="k",
    alpha=0.8,
    label="Chunks de la base",
)

# Tracer la question (en étoile rouge distincte)
plt.scatter(
    coord_query[0],
    coord_query[1],
    c="red",
    s=250,
    marker="*",
    edgecolors="k",
    label="Question posée",
)

# Annoter les chunks
for i, meta in enumerate(metadatas):
  page = meta.get("page_number", "N/A")
  label = f"{ids[i]} (p.{page})"
  plt.annotate(
      label,
      (coords_chunks[i, 0], coords_chunks[i, 1]),
      textcoords="offset points",
      xytext=(0, 8),
      ha="center",
      fontsize=7,
  )

# Annoter la question
plt.annotate(
    "QUESTION",
    (coord_query[0], coord_query[1]),
    textcoords="offset points",
    xytext=(0, 12),
    ha="center",
    fontsize=9,
    fontweight="bold",
    color="red",
)

plt.title(
    f"Espace Vectoriel 2D (PCA) - Question & Chunks\nRequête : '{query_text}'"
)
plt.xlabel("Composante 1")
plt.ylabel("Composante 2")
plt.legend(loc="upper left")
plt.grid(True, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.show()