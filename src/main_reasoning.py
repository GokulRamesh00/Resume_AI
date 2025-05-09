from data.process_data import load_documents, embed_and_store_documents, split_documents
from src.database.chroma_search_functions import get_relevant_data
from langchain.prompts import ChatPromptTemplate
from src.models.models import llama_groq
import os


def check_and_process_documents():
    # Get ChromaDB path from environment or default
    chroma_path = os.environ.get('CHROMA_PATH', "data/processed/chroma")
    print(f"Using ChromaDB path: {chroma_path}")
    
    excluded_file = "chroma.sqlite3"  # Specify the file to exclude
    print(f"Checking if path exists: {chroma_path}")
    
    def is_only_excluded_file_present():
        # Get the list of files/folders in the directory excluding hidden files (optional)
        contents = [f for f in os.listdir(chroma_path) if not f.startswith('.')]
        
        # If there's only one file and it's chroma.sqlite3, return True
        return len(contents) <= 1 and (not contents or contents[0] == excluded_file)
    
    if not os.path.exists(chroma_path) or is_only_excluded_file_present():
        print(f"Path does not exist or only {excluded_file} is present.")
        
        documents = load_documents()
        print("Documents loaded")
        
        chunks = split_documents(documents)
        print("Documents split into chunks")
        
        embed_and_store_documents(chunks)
        print("Documents embedded and stored")
    else:
        print(f"Path already exists and contains files other than {excluded_file}")
        # Continue with your existing logic here if needed




def reasoning(query, prompt):

    check_and_process_documents()

    print("#"*100 + "\n\n")
    
    results = get_relevant_data(query)

    prompt_template = ChatPromptTemplate.from_template(prompt)
    prompt = prompt_template.format(context=results, question=query)
    response = llama_groq(query, prompt)
    return response