# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain_community.document_loaders import PyPDFDirectoryLoader
# from langchain.schema.document import Document
# from FlagEmbedding.flag_models import FlagModel
# from FlagEmbedding.flag_reranker import FlagReranker\
from src.data_processing.cache_functions import get_cached_query_result, retrieve_or_initialize_cache, store_in_cache
from src.data_processing.get_embeddings import get_embeddings
from langchain_community.vectorstores import Chroma
from src.models.models import cohere_reranker
import sqlite3
import os

# Get ChromaDB path from environment variable or use default
def get_chroma_path():
    return os.environ.get('CHROMA_PATH', "data/processed/chroma")

# load the data
def get_chroma_db(get_embeddings=get_embeddings):
    chroma_path = get_chroma_path()
    print(f"Using Chroma DB at: {chroma_path}")
    return Chroma(persist_directory=chroma_path, embedding_function=get_embeddings())


def retrieve_documents(query, top_k=8):
    chroma_db = get_chroma_db()
    print("#"*100 + "\n\n")

    print("Retrieving documents...")
    results = chroma_db.similarity_search_with_score(query, top_k)
    context_text= "\n\n---\n\n".join([doc.page_content for doc, _score in results])

    print("Documents before reranking: ", context_text)

    return context_text


"""
If you want to use the FlagReranker to rerank the retrieved documents, you can use the following code snippet:

    reranker = FlagModel("BAAI/bge-reranker-v2-m3", use_fp16=True)

    def reranked_documents(query, retrieved_chunks, top_k=3):
        reranked_chunks = reranker.predict(query, retrieved_chunks)
        return [chunk for chunk, _ in reranked_chunks[:top_k]]
    
    Initialize the FlagReranker
    reranker = FlagReranker('BAAI/bge-reranker-v2-m3', use_fp16=True)
    
    
I'll personally use the cohere API to rerank the documents.
"""


def format_context(context):
    return "\n\n".join([f"Chunk {i+1}: {chunk}" for i, chunk in enumerate(context)])



def add_to_chroma_db(reranked_chunks):
    chroma_db = get_chroma_db()
    chroma_db.add_documents(reranked_chunks)
    chroma_db.persist()


def reranked_documents(query, long_string, top_k=5):
    # Split the long string into individual chunks using '\n\n---\n\n' as the separator
    chunks = long_string.split("\n\n---\n\n")

    # Ensure all chunks are valid (non-empty) and strip leading/trailing whitespace
    valid_chunks = [chunk.strip() for chunk in chunks if chunk.strip()]

    if not valid_chunks:
        print("No valid chunks to rerank.")
        return []
    
    # cohere reranker
    rerank_docs = cohere_reranker(query, valid_chunks, top_k)

    print("#"*100 + "\n\n")

    # Extract and print reranked chunks using the indices from the rerank response
    reranked_chunks = [valid_chunks[result.index] for result in rerank_docs.results]
    print("Reranked Chunks:\n\n", format_context(reranked_chunks))

    return reranked_chunks
    


def get_relevant_data(query):
    cache = retrieve_or_initialize_cache()
    
    cached_result = get_cached_query_result(cache, query)
    if cached_result:
        print("retrieve results from cache.")
        return cached_result

    retrieved_chunks = retrieve_documents(query)
    reranked_chunks = reranked_documents(query, retrieved_chunks)
    store_in_cache(cache, query, reranked_chunks)
    return reranked_chunks



def close_chroma_db_connection():
    try:
        chroma_db_connection = get_chroma_db()
        if chroma_db_connection is not None:
            chroma_db_connection.delete_collection()
            chroma_db_connection.persist()
            chroma_db_connection = None

        # Forcefully close SQLite connection
        chroma_path = get_chroma_path()
        sqlite_path = os.path.join(chroma_path, 'chroma.sqlite3')
        if os.path.exists(sqlite_path):
            conn = sqlite3.connect(sqlite_path)
            conn.close()
            print(f"ChromaDB connection closed successfully for {sqlite_path}.")
    except Exception as e:
        print(f"Error closing ChromaDB connection: {e}")








