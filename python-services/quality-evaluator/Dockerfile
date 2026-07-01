# Python 3.12 quality-evaluator service (calibrated LLM-as-Judge over HTTP).
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
# AUTO backend: uses Ollama at $OLLAMA_URL when reachable, else the offline heuristic.
CMD ["uvicorn", "evaluator.service:app", "--host", "0.0.0.0", "--port", "8000"]
