from src.database.chroma_search_functions import close_chroma_db_connection
from src.data_processing.cache_functions import redis_client, redis_connected
from data.process_data import embed_and_store_documents, split_documents
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify
from src.main_reasoning import reasoning
from flask_cors import CORS
from langchain.schema.document import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from src.data_processing.get_embeddings import get_embeddings
import shutil
import time
import os
import sys
import uuid
import signal
import subprocess
import logging

app = Flask(__name__)
CORS(app)  # This allows all origins

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the upload folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'data', 'raw')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define a unique ChromaDB path based on timestamp
CHROMA_BASE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'processed', 'chroma')
os.makedirs(CHROMA_BASE_PATH, exist_ok=True)

# Clear and recreate the test directory for loaded documents
TEST_DIR = os.path.join(os.path.dirname(__file__), 'data', 'test')
if os.path.exists(TEST_DIR):
    shutil.rmtree(TEST_DIR)
os.makedirs(TEST_DIR, exist_ok=True)

# Global variable to track the current ChromaDB path
CURRENT_CHROMA_PATH = os.path.join(CHROMA_BASE_PATH, 'default')
os.makedirs(CURRENT_CHROMA_PATH, exist_ok=True)

logger.info(f"Redis Connected: {redis_connected}")
logger.info(f"Using ChromaDB path: {CURRENT_CHROMA_PATH}")

PROMPT_TEMPLATE = """
Answer this question in a clear, unboring matter, based on the following context:
{context}
-----
Answer this question based on the above context, without citing the context in your answer:
{question};/
Answer:
"""

INTERVIEW_QUESTIONS_PROMPT = """
Generate 5 specific and detailed interview questions based on the candidate's resume information in the context.
Focus on their skills, experience, education, and projects to create questions that an interviewer might actually ask them.
Format the response as a numbered list of questions (1., 2., etc.).
Make the questions challenging but fair, probing for detailed responses about their experience.
Make sure to reference specific items from their resume instead of asking generic questions.
-----
Context from resume:
{context}
-----
Generate 5 interview questions based on this resume:
"""

def stream_response(response_text):
    """Stream the response one character at a time to simulate typing."""
    delay = 0.0001  # Adjust this delay to control the typing speed
    for char in response_text:
        yield char
        time.sleep(delay)

@app.route('/query', methods=['POST'])
def handle_query():
    data = request.json
    query = data.get('query')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    
    # Check if this is a request for interview questions
    is_interview_request = "interview" in query.lower() and "question" in query.lower()
    
    # Update global reference to ensure using the right ChromaDB path
    global CURRENT_CHROMA_PATH
    # Override the path in the reasoning function
    os.environ['CHROMA_PATH'] = CURRENT_CHROMA_PATH
    
    try:
        if is_interview_request:
            # Use the specialized interview questions prompt
            response = reasoning(query, INTERVIEW_QUESTIONS_PROMPT)
        else:
            # Use the standard prompt
            response = reasoning(query, PROMPT_TEMPLATE)
        
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/interview_questions', methods=['POST'])
def handle_interview_questions():
    """Specialized endpoint for generating interview questions"""
    # Update global reference to ensure using the right ChromaDB path
    global CURRENT_CHROMA_PATH
    os.environ['CHROMA_PATH'] = CURRENT_CHROMA_PATH
    
    try:
        # Use a specialized prompt for interview questions
        response = reasoning(
            "Generate 5 specific interview questions based on my resume",
            INTERVIEW_QUESTIONS_PROMPT
        )
        
        return jsonify({"response": response})
    except Exception as e:
        logger.error(f"Error generating interview questions: {str(e)}")
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route('/upload', methods=['POST'])
def handle_upload():
    global CURRENT_CHROMA_PATH
    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Create a new unique ChromaDB path
        unique_id = str(uuid.uuid4())
        new_chroma_path = os.path.join(CHROMA_BASE_PATH, unique_id)
        os.makedirs(new_chroma_path, exist_ok=True)
        
        # Update the global variable and environment variable
        CURRENT_CHROMA_PATH = new_chroma_path
        os.environ['CHROMA_PATH'] = CURRENT_CHROMA_PATH
        
        # Clear Redis cache if available
        if redis_connected and redis_client:
            try:
                redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Error clearing Redis: {str(e)}")
        
        try:
            # Process the resume directly
            documents = []
            
            if filename.lower().endswith('.pdf'):
                # For PDF, use PyPDFLoader directly
                loader = PyPDFLoader(file_path)
                documents = loader.load()
                logger.info(f"Loaded PDF with {len(documents)} pages")
            else:
                # For non-PDF files, try to read as text
                try:
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        try:
                            text_content = content.decode('utf-8')
                        except UnicodeDecodeError:
                            return jsonify({"error": "File format not supported"}), 400
                        
                        document = Document(
                            page_content=text_content,
                            metadata={"source": file_path}
                        )
                        documents = [document]
                except Exception as e:
                    return jsonify({"error": f"Error reading file: {str(e)}"}), 500
            
            # Process documents
            if documents:
                # Copy to test directory for compatibility
                test_file_path = os.path.join(TEST_DIR, filename)
                shutil.copy(file_path, test_file_path)
                
                # Process and store in ChromaDB
                chunks = split_documents(documents)
                logger.info(f"Split into {len(chunks)} chunks")
                
                # Directly store in Chroma without using the function that might reuse paths
                try:
                    embeddings = get_embeddings()
                    Chroma.from_documents(
                        documents=chunks,
                        embedding=embeddings,
                        persist_directory=CURRENT_CHROMA_PATH
                    )
                    logger.info(f"Successfully embedded and stored {len(chunks)} chunks in {CURRENT_CHROMA_PATH}")
                except Exception as e:
                    logger.error(f"Error storing in Chroma: {str(e)}")
                    return jsonify({"error": f"Error storing in Chroma: {str(e)}"}), 500
                
                return jsonify({"message": f"File {filename} processed successfully"}), 200
            else:
                return jsonify({"error": "No content could be extracted from the file"}), 400
                
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return jsonify({"error": f"Error processing file: {str(e)}"}), 500

# Route to clear CV data
@app.route('/clear_cv_data', methods=['POST'])
def clear_cv_data():
    try:
        # Create a new unique ChromaDB path
        unique_id = str(uuid.uuid4())
        new_chroma_path = os.path.join(CHROMA_BASE_PATH, unique_id)
        os.makedirs(new_chroma_path, exist_ok=True)
        
        # Update the global variable
        global CURRENT_CHROMA_PATH
        CURRENT_CHROMA_PATH = new_chroma_path
        os.environ['CHROMA_PATH'] = CURRENT_CHROMA_PATH
        
        # Clear Redis cache if available
        if redis_connected and redis_client:
            try:
                redis_client.flushdb()
            except Exception as e:
                logger.warning(f"Error clearing Redis: {str(e)}")
        
        return jsonify({"message": "ChromaDB data cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Get current status of the ChromaDB
@app.route('/status', methods=['GET'])
def get_status():
    try:
        global CURRENT_CHROMA_PATH
        
        # Check if documents are loaded in the current ChromaDB
        chroma_exists = os.path.exists(CURRENT_CHROMA_PATH)
        chroma_populated = False
        
        if chroma_exists:
            # Check if there are files in the ChromaDB directory
            chroma_files = os.listdir(CURRENT_CHROMA_PATH)
            chroma_populated = len(chroma_files) > 0
        
        return jsonify({
            "chroma_path": CURRENT_CHROMA_PATH,
            "chroma_exists": chroma_exists,
            "chroma_populated": chroma_populated,
            "redis_connected": redis_connected
        }), 200
    except Exception as e:
        logger.error(f"Error getting status: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)