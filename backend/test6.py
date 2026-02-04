from langchain_ollama import OllamaEmbeddings
from typing import List, Dict
import chromadb
import sqlite3

class VectorStore:
    def __init__(
        self,
        sqlite_db_path: str,
        table_name: str,
        text_columns: List[str],
        id_column: str = "id",
        chroma_persistent_dir: str = "./chroma_db_dir",
        collection_name: str = "universities",
        embedding_model_name: str = "nomic-embed-text:latest"
    ):
        self.sqlite_db_path = sqlite_db_path
        self.table_name = table_name
        self.text_columns = text_columns
        self.id_column = id_column
        self.collection_name = collection_name
        
       
        print(f"Initializing embedding model: {embedding_model_name}")
        self.model = OllamaEmbeddings(model=embedding_model_name)
        
        
        try:
            test_embed = self.model.embed_query("test")
            print(f"Embedding model working. Dimension: {len(test_embed)}")
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize embedding model. "
                f"Make sure Ollama is running and model '{embedding_model_name}' is pulled.\n"
                f"Run: ollama pull {embedding_model_name}\n"
                f"Error: {e}"
            )


        self.chroma_client = chromadb.PersistentClient(path=chroma_persistent_dir)
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name
        )
        print(f"✓ Collection '{self.collection_name}' ready. Count: {self.collection.count()}")

    def fetch_data_from_sqlite(self) -> List[Dict]:
        """Fetch data from SQLite database"""
        conn = sqlite3.connect(self.sqlite_db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        columns = [self.id_column] + self.text_columns
        query = f"SELECT {', '.join(columns)} FROM {self.table_name}"
        print(f"Executing query: {query}")
        
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        data = [dict(row) for row in rows]
        print(f"✓ Fetched {len(data)} records from SQLite")
        return data

    def build_document_text(self, row: Dict) -> str:
        """Build document text from row data"""
        parts = []
        for col in self.text_columns:
            value = row.get(col)
            if value is not None and str(value).strip() != "":
                parts.append(f"{col.replace('_', ' ').title()}: {value}")
        return " | ".join(parts)

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not texts:
            raise ValueError("No texts provided for embedding")
        
        try:
            embeddings = self.model.embed_documents(texts)
            
            if embeddings is None or len(embeddings) == 0:
                raise RuntimeError(
                    "OllamaEmbeddings returned None or empty list. "
                    "Check if Ollama is running: 'ollama list'"
                )
            
            # Validate embeddings
            if len(embeddings) != len(texts):
                raise RuntimeError(
                    f"Mismatch: {len(texts)} texts but {len(embeddings)} embeddings"
                )
            
            return embeddings
            
        except Exception as e:
            raise RuntimeError(f"Embedding failed: {e}")

    def ingest(self, batch_size: int = 64):
        """Ingest data from SQLite into ChromaDB"""
        print("\n=== Starting ingestion ===")
        data = self.fetch_data_from_sqlite()

        if not data:
            print("No data to ingest")
            return

        documents = []
        metadatas = []
        ids = []

        # Prepare documents
        for row in data:
            doc_text = self.build_document_text(row)
            if not doc_text.strip():
                continue

            documents.append(doc_text)
            metadatas.append(row)
            ids.append(str(row[self.id_column]))

        print(f"Prepared {len(documents)} documents for embedding")

        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]

            print(f"Processing batch {i//batch_size + 1}: {len(batch_docs)} documents")
            
            embeddings = self.embed_texts(batch_docs)

            self.collection.add(
                documents=batch_docs,
                embeddings=embeddings,
                metadatas=batch_meta,
                ids=batch_ids
            )
           

        

    def query(self, query_text: str, n_results: int = 5):
        """Query the vector store"""

        
        # Generate query embedding
        query_embedding = self.model.embed_query(query_text)
        print(f"Query embedding dimension: {len(query_embedding)}")

        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return results


if __name__ == "__main__":
    # Configuration
    sqlite_db_path = "/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db"
    table_name = "universities"
    text_columns = ["name", "country", "city", "language", "overview"]
    
    # Initialize vector store
    try:
        vector_store = VectorStore(
            sqlite_db_path=sqlite_db_path,
            table_name=table_name,
            text_columns=text_columns,
            id_column="id",
            chroma_persistent_dir="./chroma_db_dir",
            collection_name="university_collection",
            embedding_model_name="nomic-embed-text:latest"
        )
        
        
        #vector_store.ingest()
        
        # Query
        results = vector_store.query(
            query_text="Germany university",
            n_results=3
        )
        
      
        if results["documents"] and len(results["documents"][0]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                print(f"\n--- Result {i + 1} ---")
                print(doc)
                if results["distances"]:
                    print(f"Distance: {results['distances'][0][i]:.4f}")
        else:
            print("No results found")
            
    except Exception as e:
        raise
      

      