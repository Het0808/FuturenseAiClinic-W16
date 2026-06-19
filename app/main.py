import os
import argparse
from app.core.config import Config
from app.core.retriever import RAGRetriever
from app.core.agent import RAGAgent

def run_cli():
    """
    Main entry point for the Command Line Interface (CLI).
    Parses flags and executes actions: ingestion, database reset, or query execution.
    """
    # 1. Initialize argparse to handle terminal flags (e.g. --ingest, --query, --reset)
    parser = argparse.ArgumentParser(
        description="Futurense AI Clinic Mini-Project - RAG CLI Pipeline"
    )
    
    # Flag to ingest files from a specific directory path
    parser.add_argument(
        "--ingest",
        type=str,
        help="Path to the directory containing text files to parse and index."
    )
    
    # Flag to run a single query in the terminal
    parser.add_argument(
        "--query",
        type=str,
        help="A question query to ask the RAG pipeline."
    )
    
    # Flag to clear existing database index
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear and reset the persistent ChromaDB collection."
    )
    
    # Parse the arguments from terminal input
    args = parser.parse_args()

    # 2. Check and validate environment configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"\n[CONFIGURATION ERROR] {e}\n")
        return

    # 3. Instantiate core classes
    retriever = RAGRetriever()
    agent = RAGAgent(retriever=retriever)

    # 4. Handle --reset flag
    if args.reset:
        print("\nWiping existing vector database collection...")
        retriever.reset_db()
        print("Done.\n")
        return

    # 5. Handle --ingest flag
    if args.ingest:
        print(f"\nStarting ingestion pipeline for directory: {args.ingest}")
        try:
            retriever.ingest_directory(args.ingest)
        except Exception as e:
            print(f"\n[INGESTION FAILED] {e}\n")
        return

    # 6. Handle --query flag
    if args.query:
        print(f"\nQuerying RAG Agent: '{args.query}'")
        print("Retrieving context and synthesizing answer...")
        result = agent.answer_query(args.query)
        
        # Output the answer
        print("\n" + "="*50)
        print("GENERATED RESPONSE:")
        print("="*50)
        print(result["answer"])
        print("="*50)
        
        # Output citation details
        print("\nSOURCES & CONFIDENCE:")
        for idx, src in enumerate(result["sources"]):
            print(f"[{idx + 1}] {src['source']} (Match Confidence: {src['confidence_score']})")
        print("="*50 + "\n")
        return

    # 7. Fallback: Interactive chat loop if no flags were provided
    print("\n" + "="*50)
    print("Welcome to the Futurense AI Clinic RAG CLI!")
    print("Type your questions below. Type 'exit' or 'quit' to end.")
    print("="*50)
    
    while True:
        try:
            user_input = input("\nAsk Copilot: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit"]:
                print("Goodbye!")
                break
                
            print("Processing...")
            result = agent.answer_query(user_input)
            
            print("\nAnswer:")
            print(result["answer"])
            
            print("\nCitations:")
            if result["sources"]:
                for idx, src in enumerate(result["sources"]):
                    print(f" * {src['source']} (Match Confidence: {src['confidence_score']})")
            else:
                print(" * No document sources matched this query.")
                
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    # Standard Python guard: only run CLI if this file is run directly
    run_cli()
