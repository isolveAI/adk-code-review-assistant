"""
Configuration management for the Code Review Assistant.

This module handles all configuration settings including model selection,
grading parameters, and safety limits.
"""

import os
import logging
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator
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

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        validate_assignment=True
    )

    # --- Google Cloud Configuration ---
    google_cloud_project: Optional[str] = Field(
        default=None,
        description="GCP project ID"
    )

    google_cloud_location: str = Field(
        default="us-central1",
        description="GCP region/location"
    )

    google_genai_use_vertexai: bool = Field(
        default=True,
        description="Use Vertex AI backend (True) or Google AI Studio (False)"
    )

    google_api_key: Optional[str] = Field(
        default=None,
        description="API key for Google AI Studio (if not using Vertex AI)"
    )

    # --- Agent Engine Configuration ---
    agent_engine_id: Optional[str] = Field(
        default=None,
        description="Vertex AI Agent Engine ID for session persistence"
    )

    # --- Model Configuration ---
    worker_model: str = Field(
        default="gemini-2.5-flash",
        description="Model for analysis and style checking tasks"
    )

    critic_model: str = Field(
        default="gemini-2.5-pro",
        description="Model for feedback synthesis and nuanced reasoning"
    )

    # --- Grading Parameters ---
    passing_score_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Minimum score to pass (0.0-1.0)"
    )

    style_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for style score in final grade"
    )

    test_weight: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Weight for test results in final grade"
    )

    structure_weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Weight for code structure in final grade"
    )

    # --- Safety and Limits ---
    max_code_length: int = Field(
        default=10000,
        gt=0,
        description="Maximum allowed code length in characters"
    )

    max_test_timeout: int = Field(
        default=5,
        gt=0,
        description="Maximum timeout for test execution in seconds"
    )

    max_grading_attempts: int = Field(
        default=3,
        gt=0,
        description="Maximum grading attempts per session"
    )

    max_style_issues_shown: int = Field(
        default=10,
        gt=0,
        description="Maximum number of style issues to display"
    )

    # --- Logging Configuration ---
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )

    enable_cloud_logging: bool = Field(
        default=False,
        description="Enable Google Cloud Logging"
    )

    debug_mode: bool = Field(
        default=False,
        description="Enable debug mode with verbose output"
    )

    enable_tracing: bool = Field(
        default=False,
        description="Enable distributed tracing"
    )

    # --- Runtime Configuration ---
    port: int = Field(
        default=8080,
        description="Port for web server (Cloud Run sets this)"
    )

    @model_validator(mode='after')
    def validate_weights(self):
        """Ensure grading weights sum to 1.0."""
        total = self.style_weight + self.test_weight + self.structure_weight
        if abs(total - 1.0) > 0.001:  # Allow small floating point errors
            raise ValueError(
                f"Grading weights must sum to 1.0, got {total:.3f} "
                f"(style={self.style_weight}, test={self.test_weight}, structure={self.structure_weight})"
            )
        return self

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure log level is valid."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level: {v}. Must be one of {valid_levels}")
        return v.upper()

    @field_validator('google_cloud_project')
    @classmethod
    def set_google_cloud_project(cls, v: Optional[str]) -> Optional[str]:
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

    def validate_deployment_config(self):
        """Validate that required settings are present for the deployment."""
        # Detect deployment environment
        deployment_target = "local"
        if os.getenv('K_SERVICE'):
            deployment_target = "cloud_run"
        elif self.agent_engine_id:
            deployment_target = "agent_engine"

        # Validate based on deployment
        if deployment_target == "cloud_run":
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required for Cloud Run deployment")

        elif deployment_target == "agent_engine":
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required for Agent Engine deployment")

        # Validate auth
        if self.google_genai_use_vertexai:
            if not self.google_cloud_project:
                raise ValueError("Google Cloud Project required when using Vertex AI")
        else:
            if not self.google_api_key:
                raise ValueError("Google API Key required when not using Vertex AI")

        logger.info(f"Deployment target: {deployment_target}")


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
logger.info(f"  Project: {config.google_cloud_project}")
logger.info(f"  Models: worker={config.worker_model}, critic={config.critic_model}")
logger.info(f"  Weights: style={config.style_weight}, test={config.test_weight}, structure={config.structure_weight}")
logger.info(f"  Debug: {config.debug_mode}")
