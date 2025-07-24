#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
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

print_status "🚀 Starting Deep Paper development environment setup..."

# Check if we're in the right directory
if [[ ! -f "README.md" ]] || [[ ! -d "backend" ]] || [[ ! -d "frontend" ]]; then
    print_error "Please run this script from the root of the deep-paper repository"
    exit 1
fi

# Check for required tools
print_status "Checking for required tools..."

if ! command_exists docker; then
    print_error "Docker is required but not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    print_error "Docker Compose is required but not installed. Please install Docker Compose first."
    exit 1
fi

if ! command_exists node; then
    print_error "Node.js is required but not installed. Please install Node.js 18+ first."
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is required but not installed. Please install npm first."
    exit 1
fi

# Check for uv, install if not present
if ! command_exists uv; then
    print_warning "uv not found. Installing uv for Python dependency management..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    
    if ! command_exists uv; then
        print_error "Failed to install uv. Please install manually: https://github.com/astral-sh/uv"
        exit 1
    fi
fi

print_status "✅ All required tools are available"

# Start services
print_status "🐳 Starting Docker services (Redis and Qdrant)..."
cd backend
docker-compose up -d

# Wait for services to be healthy
print_status "⏳ Waiting for services to be ready..."
sleep 10

# Check Redis
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    print_status "✅ Redis is ready"
else
    print_warning "Redis may not be fully ready yet"
fi

# Check Qdrant
if curl -f http://localhost:6333/healthz >/dev/null 2>&1; then
    print_status "✅ Qdrant is ready"
else
    print_warning "Qdrant may not be fully ready yet"
fi

# Setup Python backend
print_status "🐍 Setting up Python backend..."

# Create virtual environment if it doesn't exist
if [[ ! -d ".venv" ]]; then
    print_status "Creating Python virtual environment..."
    uv venv
fi

# Activate virtual environment and install dependencies
print_status "Installing Python dependencies..."
source .venv/bin/activate
uv pip install -e .
uv pip install -e ".[dev]"

print_status "✅ Backend dependencies installed"

# Setup frontend
print_status "⚛️  Setting up frontend..."
cd ../frontend

if [[ -f "package-lock.json" ]]; then
    print_status "Running npm ci for faster, reliable installs..."
    npm ci
else
    print_status "Running npm install..."
    npm install
fi

print_status "✅ Frontend dependencies installed"

# Go back to root
cd ..

# Check for .env file
print_status "🔧 Checking environment configuration..."
if [[ ! -f "backend/.env" ]]; then
    if [[ -f "backend/.env.example" ]]; then
        print_warning "No .env file found. Copying .env.example to .env"
        cp backend/.env.example backend/.env
        print_warning "Please edit backend/.env with your API keys before running the application"
    else
        print_warning "No .env or .env.example file found. You may need to create backend/.env with required API keys"
    fi
else
    print_status "✅ Environment file exists"
fi

# Create start script for convenience
print_status "📝 Creating convenience scripts..."

cat > start-dev.sh << 'EOF'
#!/bin/bash
# Convenience script to start all development services

# Colors
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}Starting development environment...${NC}"

# Start backend in background
cd backend
source .venv/bin/activate
fastapi dev main.py &
BACKEND_PID=$!

# Start frontend in background  
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo -e "${GREEN}✅ Services started!${NC}"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Redis: localhost:6379"
echo "Qdrant: http://localhost:6333"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
EOF

chmod +x start-dev.sh

print_status "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit backend/.env with your API keys (if not already done)"
echo "2. Run ./start-dev.sh to start all development services"
echo "   OR start services individually:"
echo "   - Backend: cd backend && source .venv/bin/activate && fastapi dev main.py"
echo "   - Frontend: cd frontend && npm run dev"
echo ""
echo "🌐 URLs:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- Qdrant UI: http://localhost:6333/dashboard"
echo ""
echo "🔧 Development commands:"
echo "Backend:"
echo "  - Format: cd backend && black ."
echo "  - Lint: cd backend && ruff check"
echo "  - Type check: cd backend && mypy"
echo "  - Test: cd backend && pytest"
echo ""
echo "Frontend:"  
echo "  - Lint: cd frontend && npm run lint"
echo "  - Format: cd frontend && npm run format"
echo "  - Build: cd frontend && npm run build"