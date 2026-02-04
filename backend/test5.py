from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from pydantic import  BaseModel
from typing import List , Optional, Dict
import chromadb
from chromadb.config import Settings
import sqlite3

class VectorStore:
    def __init__(
            self,sqlite_db_path:str,
            table_name:str,
            text_columns:List[str],
            id_column: str = "id",
            chroma_persistent_dir:str="./chroma_db_dir",
            collection_name:str="universities",
            embedding_model_name:str="nomic-embed-text:latest"


    ):
        self.sqlite_db_path=sqlite_db_path
        self.table_name=table_name
        self.text_columns=text_columns
        self.id_column=id_column
        self.collection_name=collection_name
        self.model=OllamaEmbeddings(model=embedding_model_name)

        print(self.model)

       

        self.chroma_client = chromadb.Client(
                Settings(
                    persist_directory=chroma_persistent_dir,
                    anonymized_telemetry=False
                )
)

        self.collection=self.chroma_client.get_or_create_collection(
            name=self.collection_name
           
       ) 
        

    def fetch_data_from_sqlite(self)->List[Dict]:
        conn=sqlite3.connect(self.sqlite_db_path)
        conn.row_factory=sqlite3.Row
        cursor=conn.cursor()
        
        columns=[self.id_column]+self.text_columns
        query=f"SELECT {', '.join(columns)} FROM {self.table_name}"
        print(query)
        #rows=cursor.fetchall()
        cursor.execute(query)
        rows=cursor.fetchall()
        conn.close() 
        return [dict(row) for row in rows]
    

    def build_document_text(self, row: Dict) -> str:
        parts = []
        for col in self.text_columns:
            print(col)
            value = row.get(col)
            if value is not None and str(value).strip() != "":
                parts.append(f"{col.replace('_', ' ').title()}: {value}")

        return " | ".join(parts)

    
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        embeddings=self.model.embed_documents(texts)
        if embeddings is None:
            raise RuntimeError(
                "OllamaEmbeddings returned None. "
                "Check if Ollama is running and the model is pulled."
            )

        if not isinstance(embeddings, list) or len(embeddings) == 0:
            raise RuntimeError(
                f"Invalid embeddings returned: {embeddings}"
            )

        return embeddings

    
    def ingest(self, batch_size: int = 64):
        data = self.fetch_data_from_sqlite()
        print(data)

        if not data:
            return

        documents = []
        metadatas = []
        ids = []

        for row in data:
            doc_text = self.build_document_text(row)

            if not doc_text.strip():
                continue

            documents.append(doc_text)
            metadatas.append(row)
            ids.append(str(row[self.id_column]))

     

        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            batch_meta = metadatas[i:i + batch_size]

            embeddings = self.embed_texts(batch_docs)

            self.collection.add(
                documents=batch_docs,
                embeddings=embeddings,
                metadatas=batch_meta,
                ids=batch_ids
            )

            

        


    def query(self, query_text: str, n_results: int = 5):
        query_embedding = self.embed_texts([query_text])[0]
        print(query_embedding)

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return results
      


if __name__=="__main__":
    sqlite_db_path="/Users/swarajsolanke/Smart_assistant_chatbot/university_recommander/University.db"
    table_name="universities"
    text_columns=[
        "name","country","city","language","overview"
    ]
    print(text_columns)
    vectore_store=VectorStore(sqlite_db_path=sqlite_db_path,table_name=table_name,
                              text_columns=text_columns, 
                              id_column="id",
                              chroma_persistent_dir="./chroma_db_dir",collection_name="university_collection",embedding_model_name="nomic-embed-text:latest")
    
    vectore_store.ingest()
    

    results = vectore_store.query(
        query_text="Top engineering universities in USA",
        n_results=1
    )
    #print(results)

    
    for i, doc in enumerate(results["documents"][0]):
        pass
        #print(f"\nResult {i + 1}:")
        #print(doc)