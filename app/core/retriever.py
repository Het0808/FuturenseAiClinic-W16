import os
from pathlib import Path
from openai import OpenAI
import chromadb
from app.core.config import Config

class RAGRetriever:
    """
    Retriever class that handles:
    1. Parsing document files from a directory
    2. Segmenting raw texts into overlapping chunks
    3. Generating semantic vectors via OpenAI API
    4. Managing persistent index storage in ChromaDB
    5. Querying the collection for the Top-K nearest matches
    """
    
    def __init__(self):
        # Ensure our settings are valid (throws error if OPENAI_API_KEY is unset)
        Config.validate()
        
        # Initialize the official OpenAI client.
        # This client handles authentication using the API key from config.
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Initialize the persistent ChromaDB client.
        # It writes database index configurations directly to the database directory.
        self.chroma_client = chromadb.PersistentClient(path=Config.DATABASE_DIR)
        
        # Create or fetch a persistent collection in ChromaDB.
        # Metadata configuration is set to cosine similarity.
        self.collection = self.chroma_client.get_or_create_collection(
            name="futurense_clinic_collection",
            metadata={"hnsw:space": "cosine"}
        )

    def split_text_recursively(self, text: str, chunk_size: int = 800, chunk_overlap: int = 150) -> list[str]:
        """
        Splits text by preserving paragraph and sentence boundaries wherever possible.
        This represents the standard 'Recursive Character Split' design pattern.
        """
        # Split document by paragraphs first (double newline)
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_length = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_len = len(para)
            
            # If paragraph itself is larger than chunk limit, split it by sentence
            if para_len > chunk_size:
                # Flush existing accumulated chunk to free up buffer
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0
                
                # Split paragraph into sentences
                sentences = para.replace(". ", ".\n").split("\n")
                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue
                    sent_len = len(sentence)
                    
                    if sent_len > chunk_size:
                        # Fallback: if sentence is huge, split by word limits
                        words = sentence.split(" ")
                        temp_chunk = []
                        temp_len = 0
                        for word in words:
                            if temp_len + len(word) + 1 > chunk_size:
                                chunks.append(" ".join(temp_chunk))
                                # Retain overlapping words
                                overlap_words = temp_chunk[-int(chunk_overlap/10):] if len(temp_chunk) > int(chunk_overlap/10) else temp_chunk
                                temp_chunk = list(overlap_words) + [word]
                                temp_len = sum(len(w) for w in temp_chunk) + len(temp_chunk) - 1
                            else:
                                temp_chunk.append(word)
                                temp_len += len(word) + 1
                        if temp_chunk:
                            chunks.append(" ".join(temp_chunk))
                    else:
                        # Accumulate sentences in current chunk buffer
                        if current_length + sent_len + 1 > chunk_size:
                            chunks.append(" ".join(current_chunk))
                            # Keep overlap: carry over the last sentence to the next chunk
                            current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                            current_length = sum(len(x) for x in current_chunk) + len(current_chunk)
                            current_chunk.append(sentence)
                            current_length += sent_len + 1
                        else:
                            current_chunk.append(sentence)
                            current_length += sent_len + 1
            else:
                # Accumulate paragraphs in current chunk buffer
                if current_length + para_len + 2 > chunk_size:
                    chunks.append("\n\n".join(current_chunk))
                    # Carry over last paragraph for overlap
                    current_chunk = current_chunk[-1:] if len(current_chunk) > 1 else []
                    current_length = sum(len(x) for x in current_chunk) + len(current_chunk) * 2
                    current_chunk.append(para)
                    current_length += para_len + 2
                else:
                    current_chunk.append(para)
                    current_length += para_len + 2
                    
        # Flush any remaining text in the buffer
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return [c.strip() for c in chunks if c.strip()]

    def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Calls OpenAI Embedding API to generate vector vectors for a list of text chunks.
        Using batches reduces network round-trip overhead and avoids hitting rate limits.
        """
        if not texts:
            return []
        
        # Call embeddings.create using the configured model
        response = self.openai_client.embeddings.create(
            input=texts,
            model=Config.EMBEDDING_MODEL
        )
        # Extract and return the floats of high-dimensional vectors
        return [data.embedding for data in response.data]

    def get_query_embedding(self, query: str) -> list[float]:
        """
        Generates embedding for a single user query.
        """
        response = self.openai_client.embeddings.create(
            input=[query],
            model=Config.EMBEDDING_MODEL
        )
        return response.data[0].embedding

    def ingest_directory(self, data_dir: str):
        """
        Scans a directory for .txt files, chunks them, embeds them, and uploads to ChromaDB.
        """
        data_path = Path(data_dir)
        if not data_path.exists() or not data_path.is_dir():
            raise FileNotFoundError(f"Provided data directory '{data_dir}' does not exist.")

        all_chunks = []
        all_metadatas = []
        all_ids = []

        # Iterate through files in the directory
        for file_path in data_path.iterdir():
            if file_path.suffix.lower() == '.txt':
                print(f"Reading and Ingesting: {file_path.name}")
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Segment text using our recursive splitter
                chunks = self.split_text_recursively(content)

                # Tag each chunk with metadata and unique identifiers
                for idx, chunk in enumerate(chunks):
                    all_chunks.append(chunk)
                    all_metadatas.append({
                        "source": file_path.name,
                        "chunk_index": idx
                    })
                    # Formulate ID using filename and index (e.g. policy.txt_chunk_0)
                    all_ids.append(f"{file_path.name}_chunk_{idx}")

        if not all_chunks:
            print("No text documents found to index.")
            return

        print(f"Generating vectors for {len(all_chunks)} text segments...")
        
        # Batch generate embeddings in blocks of 100 to stay within payload limits
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(all_chunks), batch_size):
            batch_texts = all_chunks[i:i + batch_size]
            batch_embeddings = self.get_embeddings_batch(batch_texts)
            all_embeddings.extend(batch_embeddings)

        print("Writing text chunks and vectors into persistent ChromaDB index...")
        # Write chunks, embeddings, metadata, and IDs directly to ChromaDB
        self.collection.upsert(
            ids=all_ids,
            embeddings=all_embeddings,
            documents=all_chunks,
            metadatas=all_metadatas
        )
        print("Ingestion completed successfully.")

    def retrieve(self, query: str, k: int = None) -> list[dict]:
        """
        Converts query to vector space, queries ChromaDB, and returns structured result blocks.
        """
        if k is None:
            k = Config.RETRIEVAL_K

        # 1. Embed query
        query_vector = self.get_query_embedding(query)

        # 2. Query vector database collection
        # n_results limits the returned count to k
        results = self.collection.query(
            query_embeddings=[query_vector],
            n_results=k
        )

        formatted_matches = []
        # Parse the structured results dictionary
        if results and "documents" in results and results["documents"]:
            # Retrieve lists from matching indices
            docs = results["documents"][0]
            metadatas = results["metadatas"][0]
            ids = results["ids"][0]
            distances = results["distances"][0] if "distances" in results else [0.0] * len(docs)

            for i in range(len(docs)):
                # Convert Chroma distance score to a percentage-like confidence score
                # For cosine distance, similarity = 1.0 - distance
                confidence = round(1.0 - distances[i], 3)
                formatted_matches.append({
                    "id": ids[i],
                    "text": docs[i],
                    "metadata": metadatas[i],
                    "confidence": confidence
                })

        return formatted_matches

    def reset_db(self):
        """
        Clears the collection to allow database re-indexing.
        """
        self.chroma_client.delete_collection(name="futurense_clinic_collection")
        self.collection = self.chroma_client.get_or_create_collection(
            name="futurense_clinic_collection",
            metadata={"hnsw:space": "cosine"}
        )
        print("Database cleared and initialized.")
