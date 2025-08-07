# app.py
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import asyncio
import uuid
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

app = FastAPI()

# Add CORS middleware to allow requests from your React app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store uploaded report content in memory
# In production, use a database or file storage
report_storage: Dict[str, str] = {}

# Global variable for LLM
llm = None

# Initialize the Ollama LLM model
try:
    llm = OllamaLLM(model="llama3")
except Exception as e:
    print(f"Warning: Could not initialize Ollama LLM: {e}")
    print("Make sure Ollama is running with 'ollama serve' and the llama3 model is available")
    # We'll initialize it when needed and handle errors gracefully

# Primary Q&A prompt template
qa_prompt = PromptTemplate.from_template("""
You are a helpful assistant that answers questions about an employee's task report.

Task Report:
{report}

Manager's Question: {question}

Answer the question directly and professionally based only on the information in the report. 
If the information isn't available in the report, say so clearly.

Answer:
""")

# Follow-up suggestions prompt template
followup_prompt = PromptTemplate.from_template("""
Given the following manager's question and task report, suggest 3 intelligent follow-up questions 
that the manager might want to ask next. Make them specific and relevant to the report content.

Task Report:
{report}

Initial Question: {question}

Provide exactly 3 follow-up questions in a clean, numbered list without additional explanation.
Each question should be concise (under 10 words if possible):

""")


@app.get("/")
async def root():
    return {"message": "Task Report QA API is running"}


@app.post("/upload-report/")
async def upload_report(file: UploadFile = File(...)):
    try:
        content = await file.read()
        try:
            file_text = content.decode("utf-8")
        except UnicodeDecodeError:
            # If UTF-8 fails, try with another encoding
            file_text = content.decode("latin-1")
        
        # Generate a unique session ID
        session_id = str(uuid.uuid4())
        report_storage[session_id] = file_text
        
        return {"message": "Report uploaded successfully", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")


class QuestionRequest(BaseModel):
    question: str
    session_id: str


@app.post("/ask-question/")
async def ask_question(request: QuestionRequest):
    global llm
    
    session_id = request.session_id
    
    # Check if the report exists
    if session_id not in report_storage:
        raise HTTPException(status_code=404, detail="No report found. Please upload a report first.")
    
    report_text = report_storage[session_id]
    
    try:
        # Make sure LLM is initialized
        if llm is None:
            llm = OllamaLLM(model="llama3")
        
        # Create the chains
        qa_chain = qa_prompt | llm
        followup_chain = followup_prompt | llm
        
        # Run both tasks concurrently for better performance
        answer_task = asyncio.create_task(
            qa_chain.ainvoke({"report": report_text, "question": request.question})
        )
        
        suggestions_task = asyncio.create_task(
            followup_chain.ainvoke({"report": report_text, "question": request.question})
        )
        
        # Wait for both tasks to complete
        answer, suggestions_text = await asyncio.gather(answer_task, suggestions_task)
        
        # Parse suggestions into a list
        suggestions = parse_suggestions(suggestions_text)
        
        return {
            "answer": answer.strip(),
            "suggestions": suggestions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing question: {str(e)}")


def parse_suggestions(suggestions_text: str) -> List[str]:
    """Parse the suggestions text into a clean list of questions."""
    # Split by newlines and filter empty lines
    lines = [line.strip() for line in suggestions_text.split('\n') if line.strip()]
    
    # Extract questions (remove numbers, dashes, etc.)
    questions = []
    for line in lines:
        # Skip lines that are likely headers or explanations
        if not any(char.isdigit() for char in line[:2]) and len(questions) < 3:
            continue
            
        # Remove leading numbers, dots, parentheses, etc.
        cleaned = line
        for i, char in enumerate(line):
            if char.isalpha():
                cleaned = line[i:]
                break
            if i > 5:  # If we haven't found a letter in the first 5 chars, keep as is
                break
                
        # Add to our list if it looks like a question
        if cleaned and '?' in cleaned:
            questions.append(cleaned.strip())
        elif cleaned and len(cleaned) > 10:  # It might be a question without a question mark
            questions.append(cleaned.strip())
    
    # Ensure we have at most 3 suggestions
    return questions[:3] if questions else ["What were the main challenges?", 
                                           "What's planned for next week?", 
                                           "Is the timeline on track?"]


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)