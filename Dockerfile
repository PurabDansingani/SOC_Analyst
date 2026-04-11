FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

ENV PYTHONUNBUFFERED=1

# Create a non-root user for security in HF Spaces
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# HF Spaces expects port 7860
EXPOSE 7860

# Run the FastAPI server
CMD ["python", "server.py"]