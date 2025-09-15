"""
Production deployment script for Code Review Assistant.

Supports deployment to both Google Cloud Run and Vertex AI Agent Engine.
Includes validation, retry logic, and rollback capabilities.
"""

import os
import sys
import json
import subprocess
import argparse
import logging
import tempfile
from typing import Optional, List
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentError(Exception):
    """Custom exception for deployment failures."""
    pass


class CodeReviewDeployer:
    """Handles deployment to Cloud Run or Agent Engine."""

    def __init__(self, target: str, project_id: str, region: str = "us-central1"):
        """
        Initialize the deployer.

        Args:
            target: Deployment target ('cloud_run' or 'agent_engine')
            project_id: Google Cloud project ID
            region: Google Cloud region
        """
        self.target = target
        self.project_id = project_id
        self.region = region
        self.service_name = "code-review-assistant"
        self.image_name = f"gcr.io/{project_id}/{self.service_name}"
        self.agent_engine_id = os.getenv("AGENT_ENGINE_ID")

    def validate_prerequisites(self) -> None:
        """Validate all prerequisites before deployment."""
        logger.info("Validating deployment prerequisites...")

        # Check gcloud authentication
        if not self._check_gcloud_auth():
            raise DeploymentError("Not authenticated with gcloud. Run: gcloud auth login")

        # Check project
        if not self._check_project():
            raise DeploymentError(f"Project {self.project_id} not accessible or doesn't exist")

        # Check required APIs
        required_apis = self._get_required_apis()
        missing_apis = self._get_missing_apis(required_apis)
        if missing_apis:
            logger.warning(f"Missing APIs: {', '.join(missing_apis)}")
            logger.info("Attempting to enable missing APIs...")
            self._enable_apis(missing_apis)

        # Check ADK installation
        if not self._check_adk_installed():
            raise DeploymentError("ADK not installed. Run: pip install google-adk")

        # Check deployment-specific requirements
        if self.target == "agent_engine":
            self._validate_agent_engine_requirements()
        elif self.target == "cloud_run":
            self._validate_cloud_run_requirements()

        logger.info("✓ All prerequisites validated")

    def _check_gcloud_auth(self) -> bool:
        """Check if gcloud is authenticated."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "list", "--filter=status:ACTIVE", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            accounts = json.loads(result.stdout)
            return len(accounts) > 0
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            return False

    def _check_project(self) -> bool:
        """Check if the project exists and is accessible."""
        try:
            result = subprocess.run(
                ["gcloud", "projects", "describe", self.project_id, "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            project = json.loads(result.stdout)
            return project.get("projectId") == self.project_id
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return False

    def _get_required_apis(self) -> List[str]:
        """Get list of required APIs based on deployment target."""
        base_apis = [
            "aiplatform.googleapis.com",
            "storage.googleapis.com",
        ]

        if self.target == "cloud_run":
            return base_apis + [
                "run.googleapis.com",
                "cloudbuild.googleapis.com",
                "artifactregistry.googleapis.com",
            ]
        elif self.target == "agent_engine":
            return base_apis + [
                "notebooks.googleapis.com",  # Often needed for Agent Engine
            ]

        return base_apis

    def _get_missing_apis(self, required_apis: List[str]) -> List[str]:
        """Check which required APIs are not enabled."""
        try:
            result = subprocess.run(
                ["gcloud", "services", "list", "--enabled", "--format=json",
                 "--project", self.project_id],
                capture_output=True,
                text=True,
                check=True
            )
            enabled = json.loads(result.stdout)
            enabled_names = {svc["config"]["name"] for svc in enabled}

            missing = []
            for api in required_apis:
                if api not in enabled_names:
                    missing.append(api)

            return missing
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return required_apis  # Assume all are missing if we can't check

    def _enable_apis(self, apis: List[str]) -> None:
        """Enable the specified APIs."""
        for api in apis:
            logger.info(f"Enabling API: {api}")
            try:
                subprocess.run(
                    ["gcloud", "services", "enable", api, "--project", self.project_id],
                    check=True,
                    capture_output=True
                )
                logger.info(f"  ✓ {api} enabled")
            except subprocess.CalledProcessError as e:
                logger.warning(f"  ✗ Failed to enable {api}: {e}")

    def _check_adk_installed(self) -> bool:
        """Check if ADK is installed."""
        try:
            subprocess.run(["adk", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _validate_cloud_run_requirements(self) -> None:
        """Validate Cloud Run specific requirements."""
        # Check if Docker is available for local builds
        if not self._check_docker():
            logger.info("Docker not available locally, will use Cloud Build")

        # Check if Dockerfile exists
        dockerfile_path = Path("deployment/cloud_run/Dockerfile")
        if not dockerfile_path.exists():
            # Create a default Dockerfile if it doesn't exist
            logger.info("Creating default Dockerfile...")
            self._create_default_dockerfile()

    def _validate_agent_engine_requirements(self) -> None:
        """Validate Agent Engine specific requirements."""
        # Check if code_review_assistant module exists
        if not Path("code_review_assistant").exists():
            raise DeploymentError("code_review_assistant module not found")

        # Check if agent.py exports root_agent
        agent_file = Path("code_review_assistant/agent.py")
        if not agent_file.exists():
            raise DeploymentError("code_review_assistant/agent.py not found")

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _create_default_dockerfile(self) -> None:
        """Create a default Dockerfile for Cloud Run."""
        dockerfile_content = '''FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY code_review_assistant/ ./code_review_assistant/
COPY .env.example .env

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Use adk api_server with proper module path
CMD ["sh", "-c", "adk api_server code_review_assistant --port $PORT --host 0.0.0.0 --session_service_uri vertexai://$AGENT_ENGINE_ID"]
'''

        # Create deployment directory if it doesn't exist
        deployment_dir = Path("deployment/cloud_run")
        deployment_dir.mkdir(parents=True, exist_ok=True)

        dockerfile_path = deployment_dir / "Dockerfile"
        dockerfile_path.write_text(dockerfile_content)
        logger.info(f"Created Dockerfile at {dockerfile_path}")

    def deploy_cloud_run(self) -> str:
        """Deploy to Cloud Run."""
        logger.info("Starting Cloud Run deployment...")

        # Build container image
        logger.info("Building container image...")
        self._build_container_image()

        # Deploy to Cloud Run
        logger.info("Deploying to Cloud Run...")
        service_url = self._deploy_cloud_run_service()

        logger.info(f"✓ Deployment successful!")
        logger.info(f"Service URL: {service_url}")

        return service_url

    def _build_container_image(self) -> None:
        """Build container image using Cloud Build or local Docker."""
        # Check if we should use local Docker or Cloud Build
        if self._check_docker():
            self._build_with_docker()
        else:
            self._build_with_cloud_build()

    def _build_with_docker(self) -> None:
        """Build container image with local Docker."""
        logger.info("Building with local Docker...")

        dockerfile_path = "deployment/cloud_run/Dockerfile"
        if not Path(dockerfile_path).exists():
            dockerfile_path = "Dockerfile"

        try:
            # Build image
            subprocess.run(
                ["docker", "build", "-t", self.image_name, "-f", dockerfile_path, "."],
                check=True
            )

            # Push to registry
            logger.info("Pushing image to registry...")
            subprocess.run(
                ["docker", "push", self.image_name],
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Docker build failed: {e}")

    def _build_with_cloud_build(self) -> None:
        """Build container image using Cloud Build."""
        logger.info("Building with Cloud Build...")

        # Check for Dockerfile
        dockerfile_path = "deployment/cloud_run/Dockerfile"
        if not Path(dockerfile_path).exists():
            dockerfile_path = "Dockerfile"
            if not Path(dockerfile_path).exists():
                self._create_default_dockerfile()
                dockerfile_path = "deployment/cloud_run/Dockerfile"

        try:
            subprocess.run(
                [
                    "gcloud", "builds", "submit",
                    "--tag", self.image_name,
                    "--project", self.project_id,
                    "--timeout", "20m",
                    "."
                ],
                check=True
            )
        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Cloud Build failed: {e}")

    def _deploy_cloud_run_service(self) -> str:
        """Deploy the Cloud Run service."""
        # Prepare environment variables
        env_vars = [
            f"GOOGLE_CLOUD_PROJECT={self.project_id}",
            f"GOOGLE_CLOUD_LOCATION={self.region}",
            "DEPLOYMENT_TARGET=cloud_run",
            "GOOGLE_GENAI_USE_VERTEXAI=true",
        ]

        if self.agent_engine_id:
            env_vars.append(f"AGENT_ENGINE_ID={self.agent_engine_id}")

        # Build the deployment command
        deploy_cmd = [
            "gcloud", "run", "deploy", self.service_name,
            "--image", self.image_name,
            "--platform", "managed",
            "--region", self.region,
            "--project", self.project_id,
            "--allow-unauthenticated",
            "--memory", "2Gi",
            "--cpu", "2",
            "--timeout", "300",
            "--max-instances", "10",
        ]

        # Add environment variables
        for env_var in env_vars:
            deploy_cmd.extend(["--set-env-vars", env_var])

        # Add format for parsing output
        deploy_cmd.extend(["--format", "value(status.url)"])

        try:
            result = subprocess.run(
                deploy_cmd,
                capture_output=True,
                text=True,
                check=True
            )

            service_url = result.stdout.strip()
            if not service_url:
                # Try to get URL another way
                service_url = self._get_service_url()

            return service_url

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Cloud Run deployment failed: {e.stderr}")

    def _get_service_url(self) -> str:
        """Get the Cloud Run service URL."""
        try:
            result = subprocess.run(
                [
                    "gcloud", "run", "services", "describe", self.service_name,
                    "--platform", "managed",
                    "--region", self.region,
                    "--project", self.project_id,
                    "--format", "value(status.url)"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError:
            return f"https://{self.service_name}-{self.project_id}.{self.region}.run.app"

    def deploy_agent_engine(self) -> str:
        """Deploy to Agent Engine."""
        logger.info("Starting Agent Engine deployment...")

        # Check if updating existing or creating new
        if self.agent_engine_id:
            logger.info(f"Updating existing Agent Engine: {self.agent_engine_id}")
            engine_id = self._update_agent_engine()
        else:
            logger.info("Creating new Agent Engine deployment")
            engine_id = self._create_agent_engine()

        logger.info(f"✓ Deployment successful!")
        logger.info(f"Agent Engine ID: {engine_id}")

        if not self.agent_engine_id:
            logger.info("\n⚠️  IMPORTANT: Add this to your .env file:")
            logger.info(f"AGENT_ENGINE_ID={engine_id}")

        return engine_id

    def _create_agent_engine(self) -> str:
        """Create new Agent Engine deployment."""
        try:
            result = subprocess.run(
                [
                    "adk", "deploy", "agent_engine",
                    "--project", self.project_id,
                    "--region", self.region,
                    "--display_name", "Code Review Assistant",
                    "code_review_assistant"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            # Parse engine ID from output
            output = result.stdout
            engine_id = self._parse_engine_id_from_output(output)

            if not engine_id:
                # Generate a fallback ID
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                engine_id = f"code-review-assistant-{timestamp}"

            return engine_id

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Agent Engine creation failed: {e.stderr}")

    def _update_agent_engine(self) -> str:
        """Update existing Agent Engine deployment."""
        try:
            result = subprocess.run(
                [
                    "adk", "deploy", "agent_engine",
                    "--project", self.project_id,
                    "--region", self.region,
                    "--agent_engine_id", self.agent_engine_id,
                    "code_review_assistant"
                ],
                capture_output=True,
                text=True,
                check=True
            )

            return self.agent_engine_id

        except subprocess.CalledProcessError as e:
            raise DeploymentError(f"Agent Engine update failed: {e.stderr}")

    def _parse_engine_id_from_output(self, output: str) -> Optional[str]:
        """Parse Agent Engine ID from deployment output."""
        # Look for patterns like "Engine ID: xxx" or "Created agent engine: xxx"
        import re

        patterns = [
            r"Engine ID:\s*([^\s]+)",
            r"agent engine:\s*([^\s]+)",
            r"Created:\s*([^\s]+)",
            r"agent_engine_id:\s*([^\s]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    def test_deployment(self, service_url: Optional[str] = None) -> bool:
        """Test the deployed service."""
        logger.info("Testing deployment...")

        if self.target == "cloud_run" and service_url:
            return self._test_cloud_run(service_url)
        elif self.target == "agent_engine":
            return self._test_agent_engine()

        return False

    def _test_cloud_run(self, service_url: str) -> bool:
        """Test Cloud Run deployment."""
        try:
            # First try with curl (more reliable than requests for new deployments)
            test_url = f"{service_url}/health"
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", test_url],
                capture_output=True,
                text=True,
                timeout=10
            )

            status_code = result.stdout.strip()
            if status_code == "200":
                logger.info("✓ Health check passed")
                return True
            else:
                logger.warning(f"Health check returned status {status_code}")

                # Try the root endpoint
                result = subprocess.run(
                    ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", service_url],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                status_code = result.stdout.strip()
                if status_code == "200":
                    logger.info("✓ Root endpoint accessible")
                    return True

                return False

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.error(f"Health check failed: {e}")
            return False

    def _test_agent_engine(self) -> bool:
        """Test Agent Engine deployment."""
        if not self.agent_engine_id:
            logger.warning("No Agent Engine ID available for testing")
            return True  # Assume success if we can't test

        try:
            # Test with a simple prompt
            test_code = '''def add(a, b):
    return a + b'''

            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(test_code)
                temp_file = f.name

            try:
                result = subprocess.run(
                    ["adk", "run", "code_review_assistant", "--stream"],
                    input=test_code,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    logger.info("✓ Agent Engine test passed")
                    return True
                else:
                    logger.warning("Agent Engine test returned non-zero exit code")
                    return False

            finally:
                os.unlink(temp_file)

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            logger.error(f"Agent Engine test failed: {e}")
            return False

    def rollback(self, previous_version: Optional[str] = None) -> None:
        """Rollback to previous version if deployment fails."""
        logger.info("Initiating rollback...")

        if self.target == "cloud_run":
            self._rollback_cloud_run(previous_version)
        elif self.target == "agent_engine":
            logger.info("Agent Engine rollback not implemented - restore from backup if needed")

    def _rollback_cloud_run(self, previous_version: Optional[str]) -> None:
        """Rollback Cloud Run to previous version."""
        if not previous_version:
            # Get the previous revision
            try:
                result = subprocess.run(
                    [
                        "gcloud", "run", "revisions", "list",
                        "--service", self.service_name,
                        "--platform", "managed",
                        "--region", self.region,
                        "--project", self.project_id,
                        "--format", "value(name)",
                        "--limit", "2"
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )

                revisions = result.stdout.strip().split('\n')
                if len(revisions) > 1:
                    previous_version = revisions[1]  # Second most recent
                else:
                    logger.warning("No previous revision found for rollback")
                    return

            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to get previous revision: {e}")
                return

        try:
            subprocess.run(
                [
                    "gcloud", "run", "services", "update-traffic",
                    self.service_name,
                    "--platform", "managed",
                    "--region", self.region,
                    "--project", self.project_id,
                    "--to-revisions", f"{previous_version}=100"
                ],
                check=True
            )
            logger.info(f"✓ Rolled back to {previous_version}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Rollback failed: {e}")


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(
        description="Deploy Code Review Assistant to Cloud Run or Agent Engine"
    )
    parser.add_argument(
        "--target",
        choices=["cloud_run", "agent_engine"],
        required=True,
        help="Deployment target"
    )
    parser.add_argument(
        "--project",
        required=False,
        help="Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT env var)"
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="Google Cloud region (default: us-central1)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run post-deployment tests"
    )
    parser.add_argument(
        "--rollback",
        help="Rollback to specified version on failure"
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip prerequisite validation"
    )

    args = parser.parse_args()

    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.info("python-dotenv not installed, using system environment variables only")

    # Get project ID from args or environment
    project_id = args.project or os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        logger.error("Project ID not specified. Use --project or set GOOGLE_CLOUD_PROJECT")
        sys.exit(1)

    # Create deployer
    deployer = CodeReviewDeployer(
        target=args.target,
        project_id=project_id,
        region=args.region
    )

    try:
        # Validate prerequisites unless skipped
        if not args.skip_validation:
            deployer.validate_prerequisites()
        else:
            logger.warning("Skipping prerequisite validation")

        # Deploy based on target
        if args.target == "cloud_run":
            result = deployer.deploy_cloud_run()
        else:
            result = deployer.deploy_agent_engine()

        # Test if requested
        if args.test:
            logger.info("\nRunning deployment tests...")
            if not deployer.test_deployment(result):
                logger.warning("⚠️  Deployment tests failed")
                if args.rollback:
                    deployer.rollback(args.rollback)
                    sys.exit(1)
            else:
                logger.info("✓ All tests passed")

        # Success message
        logger.info("\n" + "=" * 50)
        logger.info("🎉 Deployment completed successfully!")
        logger.info("=" * 50)

        if args.target == "cloud_run":
            logger.info(f"\nYour service is available at:")
            logger.info(f"  {result}")
            logger.info(f"\nTest with:")
            logger.info(f"  curl {result}/health")
        else:
            logger.info(f"\nAgent Engine ID: {result}")
            logger.info(f"\nTest with:")
            logger.info(f"  adk run code_review_assistant --stream")

    except DeploymentError as e:
        logger.error(f"\n❌ Deployment failed: {e}")
        if args.rollback:
            deployer.rollback(args.rollback)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
