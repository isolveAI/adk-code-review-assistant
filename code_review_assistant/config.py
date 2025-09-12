# code_review_assistant/config.py
"""
Configuration management for the Code Review Assistant.

This module handles all configuration settings including model selection,
grading parameters, deployment targets, and safety limits.
"""

import os
import logging
from typing import Optional, Literal
from pydantic import BaseSettings, Field, validator, root_validator
import google.auth
from google.auth.exceptions import DefaultCredentialsError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AgentConfig(BaseSettings):
    """
    Production-ready configuration for the Code Review Assistant.

    Uses Pydantic for validation and supports environment variable overrides.
    All settings can be overridden via environment variables with the same name.
    """

    # --- Deployment Configuration ---
    deployment_target: Literal["local", "cloud_run", "agent_engine"] = Field(
        default="local",
        env="DEPLOYMENT_TARGET",
        description="Target deployment platform"
    )

    # --- Google Cloud Configuration ---
    google_cloud_project: Optional[str] = Field(
        default=None,
        env="GOOGLE_CLOUD_PROJECT",
        description="GCP project ID"
    )

    google_cloud_location: str = Field(
        default="us-central1",
        env="GOOGLE_CLOUD_LOCATION",
        description="GCP region/location"
    )

    google_genai_use_vertexai: bool = Field(
        default=True,
        env="GOOGLE_GENAI_USE_VERTEXAI",
        description="Use Vertex AI backend (True) or Google AI Studio (False)"
    )

    google_api_key: Optional[str] = Field(
        default=None,
        env="GOOGLE_API_KEY",
        description="API key for Google AI Studio (if not using Vertex AI)"
    )

    # --- Model Configuration ---
    worker_model: str = Field(
        default="gemini-2.0-flash",
        env="WORKER_MODEL",
        description="Model for analysis and style checking tasks"
    )

    critic_model: str = Field(
        default="gemini-2.0-pro",
        env="CRITIC_MODEL",
        description="Model for feedback synthesis and nuanced reasoning"
    )

    # --- Grading Parameters ---
    passing_score_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        env="PASSING_SCORE_THRESHOLD",
        description="Minimum score to pass (0.0-1.0)"
    )

    style_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        env="STYLE_WEIGHT",
        description="Weight for style score in final grade"
    )

    test_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        env="TEST_WEIGHT",
        description="Weight for test results in final grade"
    )

    structure_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        env="STRUCTURE_WEIGHT",
        description="Weight for code structure in final grade"
    )

    # --- Safety and Limits ---
    max_code_length: int = Field(
        default=10000,
        gt=0,
        env="MAX_CODE_LENGTH",
        description="Maximum allowed code length in characters"
    )

    max_test_timeout: int = Field(
        default=5,
        gt=0,
        env="MAX_TEST_TIMEOUT",
        description="Maximum timeout for test execution in seconds"
    )

    max_grading_attempts: int = Field(
        default=3,
        gt=0,
        env="MAX_GRADING_ATTEMPTS",
        description="Maximum grading attempts per session"
    )

    max_style_issues_shown: int = Field(
        default=10,
        gt=0,
        env="MAX_STYLE_ISSUES_SHOWN",
        description="Maximum number of style issues to display"
    )

    # --- Feature Flags ---
    enable_advanced_analysis: bool = Field(
        default=False,
        env="ENABLE_ADVANCED_ANALYSIS",
        description="Enable advanced code analysis features"
    )

    enable_ai_test_generation: bool = Field(
        default=True,
        env="ENABLE_AI_TEST_GENERATION",
        description="Enable AI-powered test generation"
    )

    enable_memory_service: bool = Field(
        default=True,
        env="ENABLE_MEMORY_SERVICE",
        description="Enable memory service for personalization"
    )

    enable_artifact_storage: bool = Field(
        default=True,
        env="ENABLE_ARTIFACT_STORAGE",
        description="Enable artifact storage for reports"
    )

    # --- Session Configuration ---
    session_service_uri: Optional[str] = Field(
        default=None,
        env="SESSION_SERVICE_URI",
        description="URI for session service (e.g., sqlite:///sessions.db)"
    )

    memory_service_uri: Optional[str] = Field(
        default=None,
        env="MEMORY_SERVICE_URI",
        description="URI for memory service (e.g., agentengine://engine-id)"
    )

    # --- Logging Configuration ---
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    enable_cloud_logging: bool = Field(
        default=False,
        env="ENABLE_CLOUD_LOGGING",
        description="Enable Google Cloud Logging"
    )

    # --- Development Settings ---
    debug_mode: bool = Field(
        default=False,
        env="DEBUG_MODE",
        description="Enable debug mode with verbose output"
    )

    enable_tracing: bool = Field(
        default=False,
        env="ENABLE_TRACING",
        description="Enable distributed tracing"
    )

    # --- Cloud Run Specific ---
    cloud_run_service_url: Optional[str] = Field(
        default=None,
        env="CLOUD_RUN_SERVICE_URL",
        description="Cloud Run service URL (auto-detected when deployed)"
    )

    port: int = Field(
        default=8080,
        env="PORT",
        description="Port for web server (Cloud Run sets this)"
    )

    # --- Agent Engine Specific ---
    agent_engine_id: Optional[str] = Field(
        default=None,
        env="AGENT_ENGINE_ID",
        description="Vertex AI Agent Engine ID"
    )

    staging_bucket: Optional[str] = Field(
        default=None,
        env="STAGING_BUCKET",
        description="GCS bucket for Agent Engine staging"
    )

    agent_engine_id: Optional[str] = Field(
        default=None,
        env="AGENT_ENGINE_ID",
        description="Vertex AI Agent Engine ID for session service"
    )

    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        validate_assignment = True

    @root_validator
    def validate_weights(cls, values):
        """Ensure grading weights sum to 1.0."""
        style_weight = values.get('style_weight', 0.3)
        test_weight = values.get('test_weight', 0.5)
        structure_weight = values.get('structure_weight', 0.2)

        total = style_weight + test_weight + structure_weight
        if abs(total - 1.0) > 0.001:  # Allow small floating point errors
            raise ValueError(
                f"Grading weights must sum to 1.0, got {total:.3f} "
                f"(style={style_weight}, test={test_weight}, structure={structure_weight})"
            )
        return values

    @validator('log_level')
    def validate_log_level(cls, v):
        """Ensure log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @validator('google_cloud_project', always=True)
    def set_google_cloud_project(cls, v):
        """Try to auto-detect GCP project if not set."""
        if v:
            return v

        # Try to get from default credentials
        try:
            _, project_id = google.auth.default()
            if project_id:
                logger.info(f"Auto-detected GCP project: {project_id}")
                return project_id
        except (DefaultCredentialsError, FileNotFoundError):
            pass

        # Check if we're in Cloud Run
        if os.getenv('K_SERVICE'):
            logger.warning("Running in Cloud Run but no project ID set")

        return v

    @validator('deployment_target', always=True)
    def detect_deployment_target(cls, v):
        """Auto-detect deployment target if not set."""
        if v != "local":
            return v

        # Check Cloud Run
        if os.getenv('K_SERVICE'):
            logger.info("Auto-detected Cloud Run environment")
            return "cloud_run"

        # Check Agent Engine (would have specific env vars)
        if os.getenv('AGENT_ENGINE_ID'):
            logger.info("Auto-detected Agent Engine environment")
            return "agent_engine"

        return v

    @validator('cloud_run_service_url', always=True)
    def set_cloud_run_url(cls, v, values):
        """Auto-detect Cloud Run service URL."""
        if v:
            return v

        if values.get('deployment_target') == 'cloud_run':
            # Cloud Run provides this
            service = os.getenv('K_SERVICE')
            if service:
                project = values.get('google_cloud_project')
                region = values.get('google_cloud_location')
                if project and region:
                    url = f"https://{service}-{project}.{region}.run.app"
                    logger.info(f"Auto-detected Cloud Run URL: {url}")
                    return url

        return v

    def configure_logging(self):
        """Configure logging based on settings."""
        logging.getLogger().setLevel(self.log_level)

        if self.enable_cloud_logging and self.google_cloud_project:
            try:
                from google.cloud import logging as cloud_logging
                client = cloud_logging.Client(project=self.google_cloud_project)
                client.setup_logging(log_level=self.log_level)
                logger.info("Cloud Logging enabled")
            except ImportError:
                logger.warning("google-cloud-logging not installed, using standard logging")
            except Exception as e:
                logger.warning(f"Failed to setup Cloud Logging: {e}")

    def get_session_service_uri(self) -> str:
        """Get the appropriate session service URI based on deployment."""
        if self.session_service_uri:
            return self.session_service_uri

        if self.deployment_target == "agent_engine" and self.agent_engine_id:
            return f"agentengine://{self.agent_engine_id}"
        elif self.deployment_target == "cloud_run":
            # Use database for Cloud Run
            return "sqlite:///sessions.db"
        else:
            # Local development
            return "sqlite:///./sessions.db"

    def get_memory_service_uri(self) -> Optional[str]:
        """Get the appropriate memory service URI based on deployment."""
        if not self.enable_memory_service:
            return None

        if self.memory_service_uri:
            return self.memory_service_uri

        if self.deployment_target == "agent_engine" and self.agent_engine_id:
            return f"agentengine://{self.agent_engine_id}"

        return None

    def validate_deployment_config(self):
        """Validate that required settings are present for the deployment target."""
        if self.deployment_target == "cloud_run":
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required for Cloud Run deployment")

        elif self.deployment_target == "agent_engine":
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required for Agent Engine deployment")
            if not self.agent_engine_id and not self.staging_bucket:
                logger.warning("No Agent Engine ID or staging bucket configured")

        # Validate auth
        if self.google_genai_use_vertexai:
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required when using Vertex AI")
        else:
            if not self.google_api_key:
                raise ValueError("Google API Key required when not using Vertex AI")


# Create global config instance
config = AgentConfig()

# Configure logging on import
config.configure_logging()

# Set environment variables that ADK expects
if config.google_cloud_project:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", config.google_cloud_project)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", config.google_cloud_location)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", str(config.google_genai_use_vertexai))
if config.google_api_key:
    os.environ.setdefault("GOOGLE_API_KEY", config.google_api_key)

# Validate deployment configuration
try:
    config.validate_deployment_config()
except ValueError as e:
    logger.warning(f"Configuration validation warning: {e}")

# Log configuration summary
logger.info(f"Code Review Assistant Configuration:")
logger.info(f"  Deployment: {config.deployment_target}")
logger.info(f"  Models: worker={config.worker_model}, critic={config.critic_model}")
logger.info(f"  Weights: style={config.style_weight}, test={config.test_weight}, structure={config.structure_weight}")
logger.info(f"  Debug: {config.debug_mode}")
