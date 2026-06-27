# Setup script for Security Copilot virtual environment
Write-Host "Setting up Security Copilot development environment..." -ForegroundColor Green

# Check if Python 3.11+ is installed
$pythonVersion = python --version 2>&1
Write-Host "Python version: $pythonVersion"

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "Virtual environment already exists" -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install requirements
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Install development dependencies
Write-Host "Installing development dependencies..." -ForegroundColor Yellow
pip install pytest pytest-asyncio black ruff mypy pre-commit

# Setup pre-commit hooks
Write-Host "Setting up pre-commit hooks..." -ForegroundColor Yellow
pre-commit install

Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "To activate the environment in the future, run: .\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
