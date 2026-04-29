"""Script to verify Qdrant connection and print existing collections."""

from qdrant_client import QdrantClient

def main():
    # Connect to local Qdrant instance
    client = QdrantClient(url="http://localhost:6333")
    
    try:
        collections = client.get_collections().collections
        print(f"Connected successfully to Qdrant!")
        print(f"Total collections found: {len(collections)}")
        for i, collection in enumerate(collections):
            print(f"  {i+1}. {collection.name}")
    except Exception as e:
        print(f"Failed to connect to Qdrant: {e}")

if __name__ == "__main__":
    main()
