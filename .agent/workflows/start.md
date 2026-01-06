---
description: Quick start the Financial Research Analyst Agent project
---

# Quick Start - Financial Research Analyst Agent

Follow these steps to set up and run the Financial Research Analyst Agent.

## Prerequisites

- Python 3.14+ installed
- OpenAI API key (optional, for full AI capabilities)

## Setup Steps

// turbo-all

1. Navigate to the project directory:

```bash
cd /Users/gopalsaini/Documents/Source/ai-agents-case-studies/financial-research-analyst-agent
```

2. Create a Python virtual environment:

```bash
python3 -m venv venv
```

3. Activate the virtual environment:

```bash
source venv/bin/activate
```

4. Install the required dependencies:

```bash
pip install -r requirements.txt
```

5. Copy the environment file template:

```bash
cp .env.example .env
```

6. (Optional) Edit `.env` to add your OpenAI API key if you want full AI agent capabilities. The project will work with mock data without API keys.

## Running the Application

### Option A: Start the API Server

```bash
python -m src.main api
```

The API will be available at http://localhost:8000

- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Option B: Use the CLI to Analyze a Stock

```bash
python -m src.cli analyze AAPL
```

### Option C: Analyze Multiple Stocks (Portfolio)

```bash
python -m src.cli portfolio AAPL GOOGL MSFT AMZN
```

### Option D: Open the Web Dashboard

Open the file `static/dashboard/index.html` in your browser for the interactive UI.

## Running Tests

```bash
pytest tests/ -v
```

## Docker Deployment (Optional)

```bash
docker-compose up -d
```

## Stopping the Application

- Press `Ctrl+C` to stop the API server
- Run `deactivate` to exit the virtual environment
