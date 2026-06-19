import os
from pathlib import Path
from dotenv import load_dotenv

# 1. Load environment variables from the .env file in the workspace root
# load_dotenv() searches for a .env file in the current directory or parents and loads it into os.environ.
load_dotenv()

class Config:
    """
    Configuration manager for the RAG pipeline.
    Loads environment variables with fallback defaults to ensure the system is stable.
    """
    
    # Retrieve the OpenAI API Key. Defaults to an empty string if not found.
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Set the base directory of the project by resolving the absolute path of this file's parent's parent's parent.
    # __file__ is a built-in variable that points to the current file's path.
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    
    # Database folder where ChromaDB will persist its index files.
    # Default path is base_dir/chroma_db (e.g., ./chroma_db) if not specified in environment.
    DATABASE_DIR: str = os.getenv("DATABASE_DIR", str(BASE_DIR / "chroma_db"))
    
    # The default chat completion model used for synthesizing answers.
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
    
    # The default embedding model used to represent documents and queries geometrically.
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Number of matching document chunks to retrieve for LLM synthesis context.
    RETRIEVAL_K: int = int(os.getenv("RETRIEVAL_K", "3"))

    @classmethod
    def validate(cls):
        """
        Checks if critical credentials are set. Raises an error if missing.
        This is run at application startup to fail fast instead of failing mid-execution.
        """
        if not cls.OPENAI_API_KEY:
            raise ValueError(
                "CRITICAL ERROR: OPENAI_API_KEY is not configured in your .env file.\n"
                "Please create a '.env' file in the root directory and add:\n"
                "OPENAI_API_KEY=your_actual_api_key"
            )
