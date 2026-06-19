import unittest
from unittest.mock import MagicMock, patch

# Import our components
from app.core.config import Config
from app.core.retriever import RAGRetriever
from app.core.agent import RAGAgent

class TestRAGComponents(unittest.TestCase):
    """
    Test suite verifying correctness of recursive chunking, config validation, 
    and RAG prompt formatting logic without triggering real network API bills.
    """

    def setUp(self):
        """
        Runs before every test. Ensures clean testing configs.
        """
        # Save active key to restore it later
        self.original_key = Config.OPENAI_API_KEY
        Config.OPENAI_API_KEY = "mock-api-key-for-testing"

    def tearDown(self):
        """
        Runs after every test. Restores original configuration state.
        """
        Config.OPENAI_API_KEY = self.original_key

    def test_config_validation_succeeds_when_key_set(self):
        """
        Asserts that Config.validate() succeeds when the key is provided.
        """
        try:
            Config.validate()
        except ValueError:
            self.fail("Config.validate() raised ValueError unexpectedly!")

    def test_config_validation_fails_when_key_empty(self):
        """
        Asserts that Config.validate() throws ValueError when the API key is missing.
        """
        Config.OPENAI_API_KEY = ""
        with self.assertRaises(ValueError):
            Config.validate()

    @patch('app.core.retriever.chromadb.PersistentClient')
    @patch('app.core.retriever.OpenAI')
    def test_recursive_chunking_logic(self, mock_openai, mock_chroma):
        """
        Tests that our custom recursive text splitter works on paragraph boundaries
        and keeps chunk sizes within limits.
        """
        retriever = RAGRetriever()
        
        # Test text with distinct paragraphs
        sample_document = (
            "Paragraph One. This is the first sentence of paragraph one. "
            "It holds some contextual facts that should stay together.\n\n"
            "Paragraph Two. This is paragraph two. It outlines an entirely "
            "separate topic and shouldn't merge with paragraph one."
        )
        
        # Chunk text with size limit of 150 characters
        chunks = retriever.split_text_recursively(sample_document, chunk_size=150, chunk_overlap=30)
        
        # Verify that splitting returned elements and chunk boundaries are respected
        self.assertTrue(len(chunks) >= 2)
        for chunk in chunks:
            # Check that each chunk is below or near limit size
            self.assertTrue(len(chunk) <= 180) # allow slight tolerance for words
            self.assertTrue(isinstance(chunk, str))

    @patch('app.core.retriever.chromadb.PersistentClient')
    @patch('app.core.agent.OpenAI')
    def test_agent_context_formatting(self, mock_agent_openai, mock_chroma):
        """
        Tests that retriever match dicts format correctly into target XML context tags.
        """
        agent = RAGAgent()
        
        # Sample document chunks mimicking ChromaDB output structure
        sample_matches = [
            {
                "id": "doc1_chunk_0",
                "text": "Admissions are open until June 30th.",
                "metadata": {"source": "admissions.txt", "chunk_index": 0},
                "confidence": 0.92
            },
            {
                "id": "doc2_chunk_1",
                "text": "Tuition fees must be paid in full by registration.",
                "metadata": {"source": "fees.txt", "chunk_index": 1},
                "confidence": 0.88
            }
        ]
        
        formatted_str = agent.format_contexts(sample_matches)
        
        # Verify XML structure output tags exist
        self.assertIn('<context id="0" source="admissions.txt">', formatted_str)
        self.assertIn('Admissions are open until June 30th.', formatted_str)
        self.assertIn('<context id="1" source="fees.txt">', formatted_str)
        self.assertIn('Tuition fees must be paid in full by registration.', formatted_str)

    @patch('app.core.retriever.chromadb.PersistentClient')
    @patch('app.core.retriever.OpenAI')
    @patch('app.core.agent.OpenAI')
    def test_agent_answering_payload(self, mock_agent_openai, mock_retriever_openai, mock_chroma):
        """
        Tests the end-to-end flow of RAGAgent.answer_query() using mock API returns.
        Checks that result holds the correct keys and cited sources list.
        """
        # Setup mock behavior for Retriever's OpenAI Client
        mock_retriever_openai_instance = MagicMock()
        mock_retriever_openai.return_value = mock_retriever_openai_instance
        
        # Mock embedding return structure for retriever
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_retriever_openai_instance.embeddings.create.return_value = mock_embedding_response
        
        # Setup mock behavior for Agent's OpenAI Client
        mock_agent_openai_instance = MagicMock()
        mock_agent_openai.return_value = mock_agent_openai_instance
        
        # Mock chat completions return payload structure for agent
        mock_chat_response = MagicMock()
        mock_chat_response.choices = [
            MagicMock(message=MagicMock(content="Mocked answer: Admissions close June 30th. [admissions.txt]"))
        ]
        mock_agent_openai_instance.chat.completions.create.return_value = mock_chat_response
        
        # Setup mock behavior for ChromaDB
        mock_chroma_instance = MagicMock()
        mock_chroma.return_value = mock_chroma_instance
        
        # Mock Chroma query matches return dict
        mock_collection = MagicMock()
        mock_chroma_instance.get_or_create_collection.return_value = mock_collection
        mock_collection.query.return_value = {
            "documents": [["Admissions are open until June 30th."]],
            "metadatas": [[{"source": "admissions.txt", "chunk_index": 0}]],
            "ids": [["doc1_chunk_0"]],
            "distances": [[0.08]]  # 1.0 - 0.08 = 0.92 confidence
        }
        
        # Run agent answering execution
        agent = RAGAgent()
        result = agent.answer_query("When do admissions close?")
        
        # Assert key attributes in resulting dictionary
        self.assertEqual(result["query"], "When do admissions close?")
        self.assertIn("Mocked answer", result["answer"])
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["source"], "admissions.txt")
        self.assertEqual(result["sources"][0]["confidence_score"], 0.92)

if __name__ == '__main__':
    unittest.main()
