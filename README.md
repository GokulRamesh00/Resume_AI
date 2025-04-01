# Resume RAG System

A powerful Retrieval-Augmented Generation (RAG) system that allows you to interact with your resume through natural language queries. This system provides intelligent responses to questions about your resume, helps with interview preparation, and offers insights about your professional experience.

## Features

- **Interactive Resume Chat**: Ask questions about your resume and get relevant answers
- **Interview Preparation**: Generate personalized interview questions based on your resume
- **Smart Document Processing**: Automatically processes and chunks your resume for efficient retrieval
- **Caching System**: Optimizes response time by caching similar queries
- **Modern UI**: Clean and intuitive React-based interface

## System Architecture

The system consists of several key components:

### 1. Document Processing
- PDF and text document support
- Intelligent text chunking with overlap
- Structured content formatting
- ChromaDB vector storage

### 2. Models Used
- **Language Model**: `llama3-70b-8192` (via Groq API)
  - Used for generating coherent responses
  - Configured with temperature=0.5, max_tokens=1024
- **Embedding Model**: `nomic-ai/nomic-embed-text-v1` (via HuggingFace)
  - Creates embeddings for document chunks and queries
  - Enables semantic search capabilities
- **Reranker**: `rerank-english-v2.0` (via Cohere API)
  - Reranks retrieved chunks for better relevance
  - Improves answer quality and accuracy
- **Cache Model**: `all-MiniLM-L6-v2`
  - Enables efficient query caching
  - Reduces redundant processing

### 3. Storage & Caching
- ChromaDB for vector storage
- Redis for query caching (with in-memory fallback)
- FAISS for similarity search in caching

## Prerequisites

- Python 3.8+
- Node.js 14+
- Redis (optional, for caching)
- API keys for:
  - Groq API
  - HuggingFace API
  - Cohere API

## Installation

1. Clone the repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:
```bash
cd frontend
npm install
```

4. Set up environment variables:
Create a `.env` file in the root directory with:
```env
GROQ_API_KEY="your_groq_key"
COHERE_API_KEY="your_cohere_key"
HUGGINGFACE_API_KEY="your_huggingface_key"
```

## Usage

1. Start the backend server:
```bash
python app.py
```

2. Start the frontend development server:
```bash
cd frontend
npm start
```

3. Start Redis (optional, for caching):
```bash
# On Windows with WSL2:
sudo service redis-server start

4. Open your browser and navigate to `http://localhost:3000`

## Project Structure

```
resume-rag/
├── data/
│   ├── processed/          # Processed data and embeddings
│   ├── raw/               # Raw uploaded documents
│   └── process_data.py    # Document processing functions
├── src/
│   ├── data_processing/   # Embedding and processing functions
│   ├── database/         # Database operations
│   ├── models/          # Model configurations
│   └── app.py           # Main application logic
├── frontend/            # React frontend application
├── tests/              # Test files
└── requirements.txt    # Python dependencies
```

## API Endpoints

- `POST /upload`: Upload a resume document
- `POST /query`: Submit a question about the resume
- `POST /interview_questions`: Generate interview questions
- `GET /status`: Check system status

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Groq](https://groq.com/) for LLM API
- [HuggingFace](https://huggingface.co/) for embedding models
- [Cohere](https://cohere.ai/) for reranking
- [ChromaDB](https://www.chromadb.dev/) for vector storage
- [Redis](https://redis.io/) for caching

