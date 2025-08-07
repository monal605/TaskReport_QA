# Task Report QA Backend

This is a FastAPI backend for analyzing employee task reports using an AI language model (Llama 3 via Ollama). It allows uploading a report, asking questions about it, and receiving both answers and suggested follow-up questions.

## Features

- Upload an employee's task report (text file)
- Ask questions about the report and get AI-generated answers
- Receive three intelligent follow-up question suggestions
- REST API endpoints for integration with a frontend (e.g., React)
- CORS enabled for frontend-backend communication

## Requirements

- Python 3.8+
- [Ollama](https://ollama.com/) running locally with the `llama3` model pulled
- Install dependencies:

    ```
    pip install fastapi uvicorn langchain_ollama langchain-core pydantic
    ```

## Usage

1. **Start Ollama** and ensure the `llama3` model is available:

    ```
    ollama serve
    ollama pull llama3
    ```

2. **Run the FastAPI server:**

    ```
    python app.py
    ```

3. **API Endpoints:**

    - `POST /upload-report/`  
      Upload a report file. Returns a `session_id`.

    - `POST /ask-question/`  
      Ask a question about the uploaded report. Requires `session_id` and `question` in the request body.

    - `GET /`  
      Health check endpoint.

## Example Request

**Upload a report:**
```bash
curl -F "file=@path/to/report.txt" http://localhost:8000/upload-report/
```

**Ask a question:**
```bash
curl -X POST http://localhost:8000/ask-question/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID", "question": "What were the main achievements this week?"}'
```

## File Structure

```
backend/
  app.py
```

