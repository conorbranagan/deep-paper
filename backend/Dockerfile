FROM python:3.11-slim

WORKDIR /

# Install uv
RUN pip install uv

# Copy backend code
COPY app pyproject.toml uv.lock .python-version .

# Install dependencies using uv
RUN uv venv && uv pip install -e .

# Railway automatically assigns port via PORT env variable
EXPOSE ${PORT:-8000}

# Command to run the application
CMD fastapi rung --host 0.0.0.0 --port ${PORT:-8000}