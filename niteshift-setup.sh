#!/bin/bash

# niteshift-setup.sh
# Automated development environment setup for deep-paper repository
# This script sets up the complete development environment for the Paper Research Assistant

set -e  # Exit on any error

echo "🚀 Starting niteshift environment setup for deep-paper..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if we're in the right directory
if [[ ! -f "README.md" ]] || [[ ! -d "backend" ]] || [[ ! -d "frontend" ]]; then
    print_error "Please run this script from the root of the deep-paper repository"
    exit 1
fi

print_status "Repository root confirmed"

# Check prerequisites
print_status "Checking prerequisites..."

# Check for Python 3.12+
if command_exists python3; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    print_status "Found Python $PYTHON_VERSION"
    if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 12) else 1)'; then
        print_warning "Python 3.12+ recommended, found $PYTHON_VERSION"
    fi
else
    print_error "Python 3 is required but not found"
    exit 1
fi

# Check for Node.js 18+
if command_exists node; then
    NODE_VERSION=$(node --version | cut -d'v' -f2)
    print_status "Found Node.js $NODE_VERSION"
    if ! node -e 'process.exit(parseInt(process.version.slice(1)) >= 18 ? 0 : 1)'; then
        print_warning "Node.js 18+ recommended, found $NODE_VERSION"
    fi
else
    print_error "Node.js is required but not found"
    exit 1
fi

# Check for npm
if ! command_exists npm; then
    print_error "npm is required but not found"
    exit 1
fi

# Check for Docker and Docker Compose
if ! command_exists docker; then
    print_error "Docker is required but not found"
    exit 1
fi

if ! command_exists docker-compose && ! docker compose version >/dev/null 2>&1; then
    print_error "Docker Compose is required but not found"
    exit 1
fi

print_success "All prerequisites found"

# Install uv if not present
if ! command_exists uv; then
    print_status "Installing uv Python package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    if ! command_exists uv; then
        print_error "Failed to install uv"
        exit 1
    fi
    print_success "uv installed successfully"
else
    print_status "uv is already installed"
fi

# Start services with Docker Compose
print_status "Starting required services (Redis, Qdrant)..."

cd backend

# Stop any existing containers
docker-compose down >/dev/null 2>&1 || true

# Start services in background
docker-compose up -d

# Wait for services to be healthy
print_status "Waiting for services to be ready..."
sleep 5

# Check if Redis is ready
if docker-compose exec -T redis redis-cli ping >/dev/null 2>&1; then
    print_success "Redis is ready"
else
    print_warning "Redis may not be fully ready yet"
fi

# Check if Qdrant is ready
if curl -f http://localhost:6333/healthz >/dev/null 2>&1; then
    print_success "Qdrant is ready"
else
    print_warning "Qdrant may not be fully ready yet"
fi

# Backend setup
print_status "Setting up backend environment..."

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_status "Creating Python virtual environment..."
    uv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source .venv/bin/activate
uv pip install -e .
uv pip install -e ".[dev]"
print_success "Python dependencies installed"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file from template..."
    cp .env.example .env
    print_warning "Please configure API keys in backend/.env before running the application"
else
    print_status ".env file already exists"
fi

cd ..

# Frontend setup
print_status "Setting up frontend environment..."

cd frontend

# Install frontend dependencies
print_status "Installing frontend dependencies..."
npm install
print_success "Frontend dependencies installed"

cd ..

# Final setup verification
print_status "Verifying setup..."

# Check backend can start (dry run)
cd backend
source .venv/bin/activate
if python -c "import app.main" >/dev/null 2>&1; then
    print_success "Backend imports successfully"
else
    print_warning "Backend may have import issues - check your .env configuration"
fi
cd ..

# Check frontend build
cd frontend
if npm run build >/dev/null 2>&1; then
    print_success "Frontend builds successfully"
    # Clean up build files
    rm -rf .next
else
    print_warning "Frontend build issues detected"
fi
cd ..

print_success "🎉 Niteshift environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure API keys in backend/.env"
echo "2. Start the backend: cd backend && source .venv/bin/activate && fastapi dev main.py"
echo "3. Start the frontend: cd frontend && npm run dev"
echo ""
echo "Services running:"
echo "- Redis: http://localhost:6379"
echo "- Qdrant: http://localhost:6333"
echo "- Backend (when started): http://localhost:8000"
echo "- Frontend (when started): http://localhost:3000"
echo ""
echo "Development commands:"
echo "Backend:"
echo "  - Format: black ."
echo "  - Lint: ruff check"
echo "  - Type check: mypy"
echo "  - Test: pytest"
echo ""
echo "Frontend:"
echo "  - Lint: npm run lint"
echo "  - Format: npm run format"
echo ""
echo "To stop services: cd backend && docker-compose down"