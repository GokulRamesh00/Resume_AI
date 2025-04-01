from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from src.data_processing.get_embeddings import get_embeddings
from langchain_community.vectorstores import Chroma
import os

# Use environment variable or default for ChromaDB path
def get_chroma_path():
    return os.environ.get('CHROMA_PATH', "data/processed/chroma")

# Default data path
DATA_PATH = os.path.join(os.path.dirname(__file__), 'test')

def load_documents():
    """Load documents from the data/test directory"""
    loader = PyPDFDirectoryLoader(DATA_PATH)
    documents = loader.load()
    print(f"Loaded {len(documents)} documents from {DATA_PATH}")
    return documents

def split_documents(documents):
    """Split documents into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    
    # Structure the content with a prompt template
    prompt_template = """
    Below are chunks of a document that can be used to answer a question.
    
    {document_content}
    """
    
    # Split documents into chunks
    chunks = text_splitter.split_documents(documents)
    
    # Apply the prompt template to each chunk
    for chunk in chunks:
        chunk.page_content = prompt_template.format(document_content=chunk.page_content)
    
    print(f"Split into {len(chunks)} chunks")
    return chunks

def embed_and_store_documents(chunks):
    """Embed and store documents in Chroma"""
    chroma_path = get_chroma_path()
    print(f"Storing documents in ChromaDB at: {chroma_path}")
    
    # Get embeddings
    embeddings = get_embeddings()
    
    # Store documents in Chroma
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=chroma_path
    )
    
    print(f"Documents embedded and stored in {chroma_path}")
    return True

