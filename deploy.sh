#!/bin/bash
# A unified script for deploying and running the Code Review Assistant.
# This is the single source of truth for all deployment and runtime configurations.

set -e

# --- Configuration ---
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT:-"your-gcp-project-id"}
GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION:-"us-central1"}
SERVICE_NAME="code-review-assistant"
DEFAULT_SQL_INSTANCE_NAME="${SERVICE_NAME}-db-instance"
DEFAULT_DB_NAME="sessions"
DEFAULT_DB_USER="adk-user"
DEFAULT_ARTIFACT_BUCKET="${SERVICE_NAME}-artifacts"

# --- Helper Functions ---

usage() {
    echo "Usage: $0 {local|cloud-run|agent-engine}"
    echo ""
    echo "Commands:"
    echo "  local         - 🚀 Run the agent locally with a purely in-memory database for quick testing."
    echo "  cloud-run     - ☁️  Deploy to Cloud Run with a user-managed Cloud SQL database for persistence."
    echo "  agent-engine  - 🧠 Deploy to Vertex AI Agent Engine for a fully managed, stateful agent endpoint."
}

validate_cloud_env() {
    if [ "$GOOGLE_CLOUD_PROJECT" == "your-gcp-project-id" ]; then
        echo "❌ Error: GOOGLE_CLOUD_PROJECT is not set. Please update your .env file or run 'gcloud config set project <id>'."
        exit 1
    fi
}

ensure_bucket_exists() {
    local BUCKET_NAME=$1
    local PURPOSE=$2

    # Remove gs:// prefix if present
    BUCKET_NAME=${BUCKET_NAME#gs://}

    if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
        echo "   - Creating ${PURPOSE} bucket: gs://${BUCKET_NAME}..."
        gsutil mb -p "$GOOGLE_CLOUD_PROJECT" -l "$GOOGLE_CLOUD_LOCATION" "gs://${BUCKET_NAME}"

        # Get the service account
        PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)")
        SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

        # Set uniform bucket-level access (recommended)
        gsutil iam ch serviceAccount:${SERVICE_ACCOUNT}:objectAdmin "gs://${BUCKET_NAME}"
        echo "   - ${PURPOSE} bucket created and permissions set successfully."
    else
        echo "   - Using existing ${PURPOSE} bucket: gs://${BUCKET_NAME}"
    fi
}

ensure_artifact_registry_exists() {
    local REPO_NAME=$1

    echo "🔍 Checking for Artifact Registry repository '$REPO_NAME'..."

    if ! gcloud artifacts repositories describe "$REPO_NAME" \
        --location="$GOOGLE_CLOUD_LOCATION" \
        --project="$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1; then

        echo "   - Creating Artifact Registry repository '$REPO_NAME'..."
        gcloud artifacts repositories create "$REPO_NAME" \
            --repository-format=docker \
            --location="$GOOGLE_CLOUD_LOCATION" \
            --project="$GOOGLE_CLOUD_PROJECT" \
            --description="Docker repository for $SERVICE_NAME"
        echo "   - Artifact Registry repository created successfully."
    else
        echo "   - Using existing Artifact Registry repository '$REPO_NAME'."
    fi
}

ensure_iam_permissions_for_cloud_run() {
    echo "🔐 Granting the Compute Engine default service account necessary permissions..."
    PROJECT_NUMBER=$(gcloud projects describe "$GOOGLE_CLOUD_PROJECT" --format="value(projectNumber)")
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"

    # Cloud SQL Client permission
    gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/cloudsql.client" \
        --condition=None \
        --quiet

    # Storage Object Admin permission for artifacts
    gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/storage.objectAdmin" \
        --condition=None \
        --quiet

    # Artifact Registry Writer permission (includes read) for Docker images
    gcloud projects add-iam-policy-binding "$GOOGLE_CLOUD_PROJECT" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/artifactregistry.writer" \
        --condition=None \
        --quiet

    echo "   - Cloud SQL Client, Storage Object Admin, and Artifact Registry Writer roles granted successfully."
}

# --- Main Script Logic ---

if [ -z "$1" ]; then
    usage
    exit 1
fi

case "$1" in
    local)
        echo "🚀 Starting local development server (In-Memory Sessions and Artifacts)..."
        adk web code_review_assistant/ --port 8080 --host 0.0.0.0 --session_service_uri "" --reload
        ;;

    cloud-run)
        validate_cloud_env
        echo "☁️  Deploying to Cloud Run with Cloud SQL Persistence..."

        # Set up artifact bucket
        if [ -z "$ARTIFACT_BUCKET" ]; then
            ARTIFACT_BUCKET="$DEFAULT_ARTIFACT_BUCKET"
        fi
        ensure_bucket_exists "$ARTIFACT_BUCKET" "artifact storage"

        if [ -z "$CLOUD_SQL_INSTANCE_NAME" ]; then
            echo "🔎 No Cloud SQL instance specified. Checking for default instance '$DEFAULT_SQL_INSTANCE_NAME'..."
            if ! gcloud sql instances describe "$DEFAULT_SQL_INSTANCE_NAME" >/dev/null 2>&1; then
                echo "   - Default instance not found. Creating a new Cloud SQL for PostgreSQL instance..."
                echo "   - This will take about 10-15 minutes."
                DB_PASSWORD=$(openssl rand -base64 16)
                gcloud sql instances create "$DEFAULT_SQL_INSTANCE_NAME" --database-version=POSTGRES_15 --region="$GOOGLE_CLOUD_LOCATION" --root-password="$DB_PASSWORD"
                gcloud sql databases create "$DEFAULT_DB_NAME" --instance="$DEFAULT_SQL_INSTANCE_NAME"
                gcloud sql users create "$DEFAULT_DB_USER" --instance="$DEFAULT_SQL_INSTANCE_NAME" --password="$DB_PASSWORD"

                echo "✅ Successfully created Cloud SQL instance and database."
                echo "   PLEASE SAVE THESE CREDENTIALS IN A SECURE LOCATION (e.g., Secret Manager):"
                echo "   --------------------------------------------------"
                echo "   CLOUD_SQL_INSTANCE_NAME: $DEFAULT_SQL_INSTANCE_NAME"
                echo "   DB_NAME:                 $DEFAULT_DB_NAME"
                echo "   DB_USER:                 $DEFAULT_DB_USER"
                echo "   DB_PASSWORD:             $DB_PASSWORD"
                echo "   --------------------------------------------------"
                export CLOUD_SQL_INSTANCE_NAME="$DEFAULT_SQL_INSTANCE_NAME"
                export DB_NAME="$DEFAULT_DB_NAME"
                export DB_USER="$DEFAULT_DB_USER"
                export DB_PASSWORD="$DB_PASSWORD"
            else
                echo "   - Found existing default instance. Using '$DEFAULT_SQL_INSTANCE_NAME'."
                export CLOUD_SQL_INSTANCE_NAME="$DEFAULT_SQL_INSTANCE_NAME"
            fi
        else
            echo "   - Using specified Cloud SQL instance: $CLOUD_SQL_INSTANCE_NAME"
        fi

        CLOUD_SQL_CONNECTION_NAME=$(gcloud sql instances describe "$CLOUD_SQL_INSTANCE_NAME" --format="value(connectionName)")
        SESSION_SERVICE_URI="postgresql+psycopg2://$DB_USER:$DB_PASSWORD@/$DB_NAME?host=/cloudsql/$CLOUD_SQL_CONNECTION_NAME"

        echo "📦 Deploying with ADK CLI..."
        echo "   - Session service: Cloud SQL (PostgreSQL)"
        echo "   - Artifact service: GCS bucket gs://$ARTIFACT_BUCKET"

        # Use ADK deploy command with artifact service URI
        adk deploy cloud_run \
            --project="$GOOGLE_CLOUD_PROJECT" \
            --region="$GOOGLE_CLOUD_LOCATION" \
            --service_name="$SERVICE_NAME" \
            --app_name="code_review_assistant" \
            --port=8080 \
            --with_ui \
            --session_service_uri="$SESSION_SERVICE_URI" \
            --artifact_service_uri="gs://$ARTIFACT_BUCKET" \
            --trace_to_cloud \
            code_review_assistant

        echo "✅ Deployment complete!"
        ;;

    agent-engine)
        validate_cloud_env
        echo "🧠 Deploying to Vertex AI Agent Engine (Fully Managed Persistence)..."
        echo "   - Enabling Cloud Trace for observability."

        # Check for staging bucket
        if [ -z "$STAGING_BUCKET" ]; then
            echo "❌ Error: STAGING_BUCKET not set. Please update your .env file."
            echo "   Example: STAGING_BUCKET=gs://your-project-staging"
            exit 1
        fi

        # Set up artifact bucket (Agent Engine also needs runtime artifact storage)
        if [ -z "$ARTIFACT_BUCKET" ]; then
            ARTIFACT_BUCKET="$DEFAULT_ARTIFACT_BUCKET"
        fi
        ensure_bucket_exists "$ARTIFACT_BUCKET" "artifact storage"

        # Note: Agent Engine handles environment variables differently
        # The ARTIFACT_BUCKET will be available to the agent code via os.environ
        export ARTIFACT_BUCKET="$ARTIFACT_BUCKET"

        if [ -n "$AGENT_ENGINE_ID" ]; then
            echo "   - Updating existing Agent Engine: $AGENT_ENGINE_ID"
            adk deploy agent_engine --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_LOCATION --staging_bucket=$STAGING_BUCKET --agent_engine_id=$AGENT_ENGINE_ID --trace_to_cloud code_review_assistant
        else
            echo "   - Creating new Agent Engine deployment."
            adk deploy agent_engine --project=$GOOGLE_CLOUD_PROJECT --region=$GOOGLE_CLOUD_LOCATION --staging_bucket=$STAGING_BUCKET --display_name="Code Review Assistant" --trace_to_cloud code_review_assistant
            echo "✅ IMPORTANT: A new Agent Engine was created. Save its ID for future updates."
        fi
        ;;

    *)
        echo "❌ Error: Invalid command '$1'"
        usage
        exit 1
        ;;
esac