import requests
import sys
import time

def upload_file(filepath):
    url = 'http://127.0.0.1:5000/upload'
    with open(filepath, 'rb') as f:
        files = {'file': f}
        response = requests.post(url, files=files)
    print(f"Upload response: {response.status_code}")
    print(response.text)
    return response.ok

def query_system(query_text):
    url = 'http://127.0.0.1:5000/query'
    data = {'query': query_text}
    response = requests.post(url, json=data)
    print(f"Query response: {response.status_code}")
    print(response.text)
    return response.ok

def test_multiple_queries():
    queries = [
        "What are the skills in the resume?",
        "What work experience does the person have?",
        "What education does the person have?",
        "What projects has the person worked on?"
    ]
    
    for query in queries:
        print(f"\n--- QUERY: {query} ---")
        query_system(query)
        time.sleep(1)  # Add a small delay between queries

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_client.py [upload|query|test] [filepath|query_text]")
        return
    
    action = sys.argv[1]
    
    if action == "upload" and len(sys.argv) >= 3:
        upload_file(sys.argv[2])
    elif action == "query" and len(sys.argv) >= 3:
        query_system(sys.argv[2])
    elif action == "test":
        test_multiple_queries()
    else:
        print("Invalid action. Use 'upload', 'query', or 'test'.")

if __name__ == "__main__":
    main() 