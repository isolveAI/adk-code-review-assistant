# 🎓 Code Review Assistant

An intelligent, multi-agent code review system powered by Google ADK and Gemini models. This assistant provides comprehensive Python code analysis including structure evaluation, PEP 8 style checking, automated testing, and personalized feedback with improvement tracking.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![ADK](https://img.shields.io/badge/Google%20ADK-1.0%2B-green)
![Gemini](https://img.shields.io/badge/Gemini-2.0-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🌟 Features

### Core Capabilities
- **🔍 Code Structure Analysis**: Parse and analyze Python code structure, identifying functions, classes, imports, and potential issues
- **📏 PEP 8 Style Checking**: Validate code against Python style guidelines with detailed violation reports and scoring
- **🧪 Automated Testing**: Generate and run appropriate test cases based on code analysis
- **💬 Personalized Feedback**: Provide constructive, encouraging feedback that adapts based on submission history
- **📊 Progress Tracking**: Monitor improvement over time with persistent grading history
- **🎯 Multi-Attempt Support**: Allow multiple submission attempts with incremental guidance

### Technical Features
- Multi-agent orchestration using ADK's Sequential and Loop agents
- Configurable LLM models (Gemini Flash for analysis, Gemini Pro for feedback)
- Session persistence with multiple backend options
- Artifact management for reports and feedback history
- Deployment ready for Vertex AI Agent Engine, Cloud Run, and GKE

## 🏛️ Architecture

The Code Review Assistant uses a sophisticated multi-agent architecture with specialized agents working in sequence to provide comprehensive code analysis:

```mermaid
flowchart TB
    %% Styling
    classDef userNode fill:#e1f5fe,stroke:#01579b,stroke-width:3px,color:#000
    classDef mainAgent fill:#fff3e0,stroke:#e65100,stroke-width:3px,color:#000
    classDef workflowAgent fill:#f3e5f5,stroke:#4a148c,stroke-width:2px,color:#000
    classDef llmAgent fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px,color:#000
    classDef tool fill:#fce4ec,stroke:#880e4f,stroke-width:2px,color:#000
    classDef storage fill:#f5f5f5,stroke:#424242,stroke-width:2px,color:#000

    %% Nodes
    User[("👤 User<br/>Submits Python Code")]:::userNode
    
    %% Main Orchestrator
    MainAgent["🎯 Main Code Review Agent<br/>(Orchestrator)"]:::mainAgent
    
    %% Workflow Agents
    Sequential["📋 Sequential Agent<br/>Manages Pipeline Flow"]:::workflowAgent
    Loop["🔄 Loop Agent<br/>Iterative Refinement<br/>(max 3 iterations)"]:::workflowAgent
    
    %% Sub-Agents
    Analyzer["🔍 Code Analyzer Agent<br/>(Gemini Flash)<br/>Parses & understands code"]:::llmAgent
    StyleChecker["📏 Style Checker Agent<br/>(Gemini Flash)<br/>PEP 8 validation"]:::llmAgent
    TestRunner["🧪 Test Runner Agent<br/>(Gemini Flash)<br/>Test generation & execution"]:::llmAgent
    Critic["🎭 Critic Agent<br/>(Gemini Flash)<br/>Reviews code quality"]:::llmAgent
    Reviser["✏️ Reviser Agent<br/>(Gemini Flash)<br/>Suggests improvements"]:::llmAgent
    FeedbackSynth["💬 Feedback Synthesizer<br/>(Gemini Pro)<br/>Personalized feedback"]:::llmAgent
    
    %% Tools
    AnalyzeTool[["🔧 analyze_code_structure()<br/>AST parsing & analysis"]]:::tool
    StyleTool[["🔧 check_code_style()<br/>pycodestyle integration"]]:::tool
    TestTool[["🔧 generate_and_run_tests()<br/>Dynamic test creation"]]:::tool
    SearchTool[["🔧 search_past_feedback()<br/>History retrieval"]]:::tool
    UpdateTool[["🔧 update_grading_progress()<br/>Progress tracking"]]:::tool
    SaveTool[["🔧 save_grading_report()<br/>Report generation"]]:::tool
    
    %% Storage
    SessionState[("💾 Session State<br/>code_to_review<br/>structure_analysis<br/>style_score<br/>test_results<br/>grading_attempts")]:::storage
    UserState[("👤 User State<br/>total_submissions<br/>past_feedback<br/>improvement_history")]:::storage
    
    %% Relationships
    User -->|"Submit Code"| MainAgent
    MainAgent --> Sequential
    
    Sequential --> Analyzer
    Sequential --> Loop
    Sequential --> FeedbackSynth
    
    Loop --> Critic
    Loop --> Reviser
    
    Analyzer -.->|uses| AnalyzeTool
    StyleChecker -.->|uses| StyleTool
    TestRunner -.->|uses| TestTool
    FeedbackSynth -.->|uses| SearchTool
    FeedbackSynth -.->|uses| UpdateTool
    FeedbackSynth -.->|uses| SaveTool
    
    %% Parallel execution within Sequential
    Sequential --> StyleChecker
    Sequential --> TestRunner
    
    %% State Management
    Analyzer ==>|writes| SessionState
    StyleChecker ==>|writes| SessionState
    TestRunner ==>|writes| SessionState
    Critic ==>|reads/writes| SessionState
    Reviser ==>|reads/writes| SessionState
    FeedbackSynth ==>|reads| SessionState
    FeedbackSynth ==>|reads/writes| UserState
    
    %% Data Flow Labels
    Analyzer -.->|"code_analysis"| SessionState
    StyleChecker -.->|"style_score, issues"| SessionState
    TestRunner -.->|"test_results"| SessionState
    
    %% Output
    FeedbackSynth -->|"Final Feedback"| User
```

### Architecture Components

#### 🎯 **Main Orchestrator**
- **CodeReviewAgent**: Entry point that coordinates the entire review process
- Routes user input through the agent pipeline
- Manages session and state persistence

#### 📋 **Workflow Management**
- **SequentialAgent**: Controls the main pipeline flow (Analysis → Refinement → Feedback)
- **LoopAgent**: Handles iterative refinement with Critic and Reviser agents (max 3 iterations)

#### 🤖 **Specialized LLM Agents**
1. **Code Analyzer** (Gemini Flash)
   - Parses Python code using AST
   - Identifies functions, classes, imports
   - Detects structural issues
   
2. **Style Checker** (Gemini Flash)
   - Validates PEP 8 compliance
   - Calculates style score (0-100)
   - Reports specific violations with line numbers
   
3. **Test Runner** (Gemini Flash)
   - Generates appropriate test cases
   - Executes tests in isolated subprocess
   - Reports pass/fail statistics
   
4. **Critic & Reviser** (Gemini Flash)
   - Work in tandem within the Loop Agent
   - Critic identifies issues, Reviser suggests fixes
   - Iteratively improve code quality
   
5. **Feedback Synthesizer** (Gemini Pro)
   - Combines all analysis results
   - Retrieves historical feedback
   - Generates personalized, constructive feedback

#### 🔧 **Tool Functions**
- **analyze_code_structure()**: AST-based code parsing
- **check_code_style()**: pycodestyle integration
- **generate_and_run_tests()**: Dynamic test generation and execution
- **search_past_feedback()**: Historical feedback retrieval
- **update_grading_progress()**: Progress tracking
- **save_grading_report()**: Artifact generation

#### 💾 **State Management**
- **Session State**: Temporary data for current review
- **User State**: Persistent user history and preferences
- **Artifact Storage**: Reports and feedback archives

## 📋 Prerequisites

- Python 3.10 or higher
- Google Cloud Project (for Vertex AI) or Google AI Studio API key
- Git for version control
- (Optional) Docker for containerized deployment

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/ayoisio/code-review-assistant.git
cd code-review-assistant
```

### 2. Set Up Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or using Poetry (recommended)
poetry install
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or use your preferred editor
```

Key configuration options:
- `GOOGLE_CLOUD_PROJECT`: Your GCP project ID
- `GOOGLE_GENAI_USE_VERTEXAI`: Set to `true` for Vertex AI, `false` for AI Studio
- `GOOGLE_API_KEY`: Your API key (if using AI Studio)

### 4. Run the Assistant

#### Web Interface (Recommended)
```bash
adk web code_review_assistant/
```
Navigate to `http://localhost:8080` in your browser.

#### Command Line
```bash
adk run code_review_assistant/
```

#### API Server
```bash
adk api_server code_review_assistant/
```

## 🏗️ Project Structure

```
code-review-assistant/
├── code_review_assistant/
│   ├── __init__.py
│   ├── agent.py                 # Main agent orchestration
│   ├── config.py                 # Configuration management
│   ├── tools.py                  # Tool implementations
│   └── sub_agents/               # Individual agent modules
│       ├── code_analyzer.py
│       ├── style_checker.py
│       ├── test_runner.py
│       └── feedback_synthesizer.py
├── test_code_inputs/             # Sample code for testing
│   ├── good_code.py
│   ├── needs_linting.py
│   ├── failing_tests.py
│   └── test_cases.json
├── deployment/
│   └── deploy.py                 # Deployment automation script
├── tests/                        # Unit and integration tests
├── docs/                         # Additional documentation
├── .env.example                  # Environment variable template
├── pyproject.toml                # Project dependencies and metadata
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## 🔧 Configuration

### Model Selection

The assistant uses two Gemini models configured in `config.py`:

```python
# Fast model for analysis tasks
worker_model = "gemini-2.5-flash"

# Advanced model for nuanced feedback
critic_model = "gemini-2.5-pro"
```

### Grading Parameters

Adjust grading thresholds in your `.env` file:

```bash
PASSING_SCORE_THRESHOLD=0.8
STYLE_WEIGHT=0.3
TEST_WEIGHT=0.5
STRUCTURE_WEIGHT=0.2
MAX_GRADING_ATTEMPTS=3
```

### Session Management

Choose your session backend:

```bash
# Local development (SQLite)
SESSION_SERVICE_URI=sqlite:///./sessions.db

# Production (PostgreSQL)
SESSION_SERVICE_URI=postgresql://user:pass@host/db

# Vertex AI managed sessions
SESSION_SERVICE_URI=vertexai://agent-engine-id
```

## 🎯 Usage Examples

### Basic Code Review

```python
# Submit code for review
code = """
def add(a, b):
    return a + b

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
"""

# The assistant will:
# 1. Analyze code structure
# 2. Check PEP 8 compliance
# 3. Generate and run tests
# 4. Provide comprehensive feedback
```

### Testing Sample Files

The project includes test files in `test_code_inputs/`:

1. **good_code.py**: Well-written code that should pass all checks
2. **needs_linting.py**: Code with style violations
3. **failing_tests.py**: Code with logical errors

### API Usage

```python
import requests

# Submit code for review
response = requests.post(
    "http://localhost:8080/run_sse",
    json={
        "app_name": "code_review_assistant",
        "user_id": "student_123",
        "session_id": "session_abc",
        "new_message": {
            "role": "user",
            "parts": [{"text": "Review this code:\n\ndef hello():\n    print('Hello')"}]
        },
        "streaming": False
    }
)

print(response.json())
```

## 🚢 Deployment

### Local Development

```bash
# Run with hot reload
adk web code_review_assistant/ --reload

# Run with custom port
adk web code_review_assistant/ --port 3000
```

### Vertex AI Agent Engine

```bash
# Test locally first
python deployment/deploy.py --test_local

# Deploy to Agent Engine
python deployment/deploy.py --create \
    --project_id=your-project \
    --location=us-central1 \
    --bucket=your-staging-bucket

# List deployed agents
python deployment/deploy.py --list

# Delete an agent
python deployment/deploy.py --delete --resource_id=agent-id
```

### Cloud Run

```bash
# Using ADK CLI
adk deploy cloud_run \
    --project=your-project \
    --region=us-central1 \
    --with_ui \
    code_review_assistant/

# Using gcloud
gcloud run deploy code-review-assistant \
    --source . \
    --region us-central1 \
    --allow-unauthenticated
```

### Google Kubernetes Engine (GKE)

```bash
# Deploy to GKE
adk deploy gke \
    --project=your-project \
    --cluster_name=your-cluster \
    --region=us-central1 \
    --with_ui \
    code_review_assistant/
```

## 🧪 Testing

### Run Unit Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=code_review_assistant --cov-report=html

# Run specific test file
pytest tests/test_tools.py
```

### Run Integration Tests

```bash
# Test agent evaluation
pytest tests/integration/

# Test with specific fixture
pytest tests/integration/test_agent_evaluation.py
```

### Code Quality Checks

```bash
# Format code
black code_review_assistant/

# Check style
flake8 code_review_assistant/

# Type checking
mypy code_review_assistant/

# All checks
pre-commit run --all-files
```

## 📊 Monitoring and Debugging

### View Logs

```bash
# ADK logs
tail -f ~/.adk/logs/agent.log

# Application logs
tail -f logs/code_review_assistant.log
```

### Debug Mode

Set in `.env`:
```bash
DEBUG_MODE=true
LOG_LEVEL=DEBUG
ENABLE_TRACING=true
```

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Write docstrings for all public functions
- Add unit tests for new features

---

Built with ❤️ using [Google ADK](https://ai.google.dev/adk) and [Gemini](https://ai.google.dev/gemini)