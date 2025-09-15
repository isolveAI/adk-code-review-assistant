#!/bin/bash

# deployment/deploy.sh
# Deployment script for Code Review Assistant

set -e  # Exit on error

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Validate required environment variables
validate_env() {
    if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
        echo "Error: GOOGLE_CLOUD_PROJECT not set"
        exit 1
    fi
    if [ -z "$GOOGLE_CLOUD_LOCATION" ]; then
        echo "Error: GOOGLE_CLOUD_LOCATION not set"
        exit 1
    fi
}

# Deploy to Agent Engine
deploy_agent_engine() {
    echo "Deploying to Agent Engine..."
    validate_env

    # Check if AGENT_ENGINE_ID exists for update vs create
    if [ -n "$AGENT_ENGINE_ID" ]; then
        echo "Updating existing Agent Engine: $AGENT_ENGINE_ID"
        adk deploy agent_engine \
            --project=$GOOGLE_CLOUD_PROJECT \
            --region=$GOOGLE_CLOUD_LOCATION \
            --agent_engine_id=$AGENT_ENGINE_ID \
            code_review_assistant
    else
        echo "Creating new Agent Engine deployment"
        adk deploy agent_engine \
            --project=$GOOGLE_CLOUD_PROJECT \
            --region=$GOOGLE_CLOUD_LOCATION \
            --display_name="Code Review Assistant" \
            code_review_assistant
        echo "Remember to save the Agent Engine ID to your .env file!"
    fi
}

# Deploy to Cloud Run
deploy_cloud_run() {
    echo "Building and deploying to Cloud Run..."
    validate_env

    if [ -z "$AGENT_ENGINE_ID" ]; then
        echo "Warning: AGENT_ENGINE_ID not set - session persistence will not work across deployments"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    # Build and deploy using source
    gcloud run deploy code-review-assistant \
        --source . \
        --region=$GOOGLE_CLOUD_LOCATION \
        --project=$GOOGLE_CLOUD_PROJECT \
        --set-env-vars="AGENT_ENGINE_ID=$AGENT_ENGINE_ID,GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION" \
        --memory=2Gi \
        --cpu=2 \
        --timeout=300 \
        --allow-unauthenticated

    echo "Cloud Run deployment complete!"
    echo "Service URL will be displayed above"
}

# Run local API server (headless)
run_api_server() {
    echo "Starting local API server (headless)..."
    validate_env

    local port=${PORT:-8080}
    local session_uri=""

    # Configure session service based on AGENT_ENGINE_ID
    if [ -n "$AGENT_ENGINE_ID" ]; then
        session_uri="--session_service_uri vertexai://$AGENT_ENGINE_ID"
        echo "Using VertexAI session service with Agent Engine ID: $AGENT_ENGINE_ID"
    else
        session_uri="--session_service_uri sqlite:///./sessions.db"
        echo "Using local SQLite session storage"
    fi

    echo "Starting API server on http://localhost:$port"
    echo "API endpoints:"
    echo "  - POST http://localhost:$port/run_sse"
    echo "  - GET  http://localhost:$port/list-apps"
    echo ""
    echo "Press Ctrl+C to stop"

    adk api_server code_review_assistant \
        --port=$port \
        --host=0.0.0.0 \
        $session_uri \
        --reload
}

# Run local web UI
run_web() {
    echo "Starting local web UI..."
    validate_env

    local port=${PORT:-8080}
    local session_uri=""

    # Configure session service based on AGENT_ENGINE_ID
    if [ -n "$AGENT_ENGINE_ID" ]; then
        session_uri="--session_service_uri vertexai://$AGENT_ENGINE_ID"
        echo "Using VertexAI session service with Agent Engine ID: $AGENT_ENGINE_ID"
    else
        session_uri="--session_service_uri sqlite:///./sessions.db"
        echo "Using local SQLite session storage"
    fi

    echo "Starting web UI on http://localhost:$port"
    echo "The browser should open automatically..."
    echo ""
    echo "Features:"
    echo "  - Interactive chat interface"
    echo "  - Session management"
    echo "  - Code input with syntax highlighting"
    echo ""
    echo "Press Ctrl+C to stop"

    adk web code_review_assistant \
        --port=$port \
        --host=0.0.0.0 \
        $session_uri \
        --reload
}

# Test the agent locally
test_agent() {
    echo "Testing agent locally..."
    validate_env

    local test_code='def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(x, y):
    """Multiply two numbers."""
    return x * y

# Test the functions
if __name__ == "__main__":
    print(add(2, 3))
    print(multiply(4, 5))'

    echo "Submitting test code for review..."
    echo "$test_code" | adk run code_review_assistant --stream
}

# Show deployment status
status() {
    echo "Code Review Assistant Deployment Status"
    echo "========================================"
    echo ""

    # Check environment
    echo "Environment Configuration:"
    echo "  Project: ${GOOGLE_CLOUD_PROJECT:-NOT SET}"
    echo "  Location: ${GOOGLE_CLOUD_LOCATION:-NOT SET}"
    echo "  Agent Engine ID: ${AGENT_ENGINE_ID:-NOT SET}"
    echo ""

    # Check Cloud Run deployment
    echo "Cloud Run Status:"
    if [ -n "$GOOGLE_CLOUD_PROJECT" ]; then
        gcloud run services describe code-review-assistant \
            --region=$GOOGLE_CLOUD_LOCATION \
            --project=$GOOGLE_CLOUD_PROJECT \
            --format="value(status.url)" 2>/dev/null || echo "  Not deployed"
    else
        echo "  Cannot check - project not set"
    fi
    echo ""

    # Check Agent Engine deployment
    echo "Agent Engine Status:"
    if [ -n "$AGENT_ENGINE_ID" ]; then
        echo "  Engine ID configured: $AGENT_ENGINE_ID"
    else
        echo "  Not configured"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 {agent-engine|cloud-run|api-server|web|test|status}"
    echo ""
    echo "Deployment Commands:"
    echo "  agent-engine  - Deploy to Vertex AI Agent Engine"
    echo "  cloud-run     - Deploy to Google Cloud Run"
    echo ""
    echo "Local Development Commands:"
    echo "  api-server    - Run local API server (headless)"
    echo "  web           - Run local web UI with chat interface"
    echo "  test          - Test the agent with sample code"
    echo ""
    echo "Utility Commands:"
    echo "  status        - Show deployment status"
    echo ""
    echo "Ensure your .env file is configured with required variables"
}

# Main script logic
case "$1" in
    agent-engine)
        deploy_agent_engine
        ;;
    cloud-run)
        deploy_cloud_run
        ;;
    api-server)
        run_api_server
        ;;
    web)
        run_web
        ;;
    test)
        test_agent
        ;;
    status)
        status
        ;;
    *)
        usage
        exit 1
        ;;
esac