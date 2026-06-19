from openai import OpenAI
from app.core.config import Config
from app.core.retriever import RAGRetriever
from app.core.prompts import RAG_SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

class RAGAgent:
    """
    RAGAgent orchestrates the end-to-end question-answering workflow:
    1. Triggers retrieval of matching document chunks.
    2. Builds the context string block.
    3. Merges context into prompt templates.
    4. Executes OpenAI Chat Completion API call.
    5. Structurizes response payloads, including citation references.
    """
    
    def __init__(self, retriever: RAGRetriever = None):
        # Allow passing an existing retriever instance to share memory/DB connections,
        # or instantiate a new one by default.
        self.retriever = retriever if retriever is not None else RAGRetriever()
        
        # Instantiate the OpenAI client.
        self.openai_client = OpenAI(api_key=Config.OPENAI_API_KEY)

    def format_contexts(self, matches: list[dict]) -> str:
        """
        Transforms retrieved document chunks into a structured, labeled text block.
        Using XML-like markers (<context>) helps the LLM isolate different documents.
        """
        if not matches:
            return "No matching documentation found."
            
        formatted_blocks = []
        for idx, match in enumerate(matches):
            source_file = match["metadata"].get("source", "Unknown Source")
            chunk_text = match["text"]
            # Formatting as:
            # <context id="0" source="filename.txt">
            # chunk content
            # </context>
            block = f'<context id="{idx}" source="{source_file}">\n{chunk_text}\n</context>'
            formatted_blocks.append(block)
            
        return "\n\n".join(formatted_blocks)

    def answer_query(self, query: str) -> dict:
        """
        Receives query, runs retrieval, structures prompt, calls LLM, and outputs result + sources.
        """
        # 1. Retrieve the top K matching document segments
        matches = self.retriever.retrieve(query, k=Config.RETRIEVAL_K)
        
        # 2. Format the matching segments into a single context string
        context_str = self.format_contexts(matches)
        
        # 3. Inject context string into our system prompt template
        system_prompt = RAG_SYSTEM_PROMPT.format(context_str=context_str)
        
        # 4. Inject query into our user prompt template
        user_prompt = USER_PROMPT_TEMPLATE.format(query_str=query)
        
        # 5. Execute LLM generation call
        # We set temperature=0.0 to ensure deterministic, highly factual responses.
        response = self.openai_client.chat.completions.create(
            model=Config.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0
        )
        
        # Extract response text
        answer_text = response.choices[0].message.content
        
        # 6. Extract unique sources that were retrieved for auditing purposes
        # We gather filenames and match confidence percentages from the metadata.
        sources_list = []
        seen_sources = set()
        
        for m in matches:
            src_name = m["metadata"].get("source", "Unknown Source")
            confidence = m["confidence"]
            # Deduplicate matching files while retaining their confidence scores
            if src_name not in seen_sources:
                seen_sources.add(src_name)
                sources_list.append({
                    "source": src_name,
                    "confidence_score": confidence
                })
        
        # Return structured output dictionary
        return {
            "query": query,
            "answer": answer_text,
            "sources": sources_list,
            "raw_matches": matches
        }
