# MRO Backend Service
FastAPI entrypoint and LangGraph Agentic routing layer.

## Setup
1. Create a virtual environment and install requirements:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Start the API server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
