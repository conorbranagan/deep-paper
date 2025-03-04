FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy backend code
COPY backend/ .

# Install dependencies using uv
RUN uv pip install -e .

# Railway automatically assigns port via PORT env variable
EXPOSE ${PORT:-8000}

# Command to run the application
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}