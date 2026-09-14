import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="rag_chunks")

print(f"📦 Nombre total de chunks stockés : {collection.count()}")
print("\n🔍 Aperçu des 2 premiers éléments :")
print(collection.peek(limit=2))