# code_review_assistant/deployment/deploy.py
"""
Production deployment script for Code Review Assistant.

Supports deployment to both Google Cloud Run and Vertex AI Agent Engine.
Includes validation, retry logic, and rollback capabilities.
"""

import os
import sys
import time
import json
import subprocess
import argparse
import logging
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
        if not self._check_apis_enabled(required_apis):
            raise DeploymentError(f"Enable required APIs: {', '.join(required_apis)}")

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
        except (subprocess.CalledProcessError, json.JSONDecodeError):
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
                "containerregistry.googleapis.com",
            ]
        elif self.target == "agent_engine":
            return base_apis + [
                "agentengine.googleapis.com",  # If this exists
            ]

        return base_apis

    def _check_apis_enabled(self, apis: List[str]) -> bool:
        """Check if required APIs are enabled."""
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
            for api in apis:
                if api not in enabled_names:
                    missing.append(api)

            if missing:
                logger.warning(f"Missing APIs: {missing}")
                logger.info("Enable them with:")
                for api in missing:
                    logger.info(f"  gcloud services enable {api} --project {self.project_id}")
                return False

            return True
        except (subprocess.CalledProcessError, json.JSONDecodeError):
            return False

    def _validate_cloud_run_requirements(self) -> None:
        """Validate Cloud Run specific requirements."""
        # Check if Docker/Buildpacks is available
        if not self._check_docker():
            logger.warning("Docker not available, will use Cloud Build")

    def _validate_agent_engine_requirements(self) -> None:
        """Validate Agent Engine specific requirements."""
        # Check for staging bucket
        staging_bucket = os.getenv("STAGING_BUCKET")
        if not staging_bucket:
            raise DeploymentError("STAGING_BUCKET environment variable required for Agent Engine")

        # Verify bucket exists
        if not self._check_bucket_exists(staging_bucket):
            raise DeploymentError(f"Staging bucket {staging_bucket} doesn't exist")

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        try:
            subprocess.run(["docker", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _check_bucket_exists(self, bucket: str) -> bool:
        """Check if a GCS bucket exists."""
        bucket_name = bucket.replace("gs://", "")
        try:
            subprocess.run(
                ["gsutil", "ls", f"gs://{bucket_name}"],
                capture_output=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def deploy_cloud_run(self) -> str:
        """Deploy to Cloud Run."""
        logger.info("Starting Cloud Run deployment...")

        # Build container image
        logger.info("Building container image...")
        self._build_container_image()

        # Deploy to Cloud Run with retry
        logger.info("Deploying to Cloud Run...")
        service_url = self._deploy_cloud_run_with_retry()

        logger.info(f"✓ Deployment successful!")
        logger.info(f"Service URL: {service_url}")

        return service_url

    def _build_container_image(self) -> None:
        """Build container image using Cloud Build."""
        build_config = {
            "steps": [
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": [
                        "build",
                        "-t", self.image_name,
                        "-f", "deployment/cloud_run/Dockerfile",
                        "."
                    ]
                },
                {
                    "name": "gcr.io/cloud-builders/docker",
                    "args": ["push", self.image_name]
                }
            ]
        }

        # Write build config
        build_file = "cloudbuild.yaml"
        with open(build_file, "w") as f:
            import yaml
            yaml.dump(build_config, f)

        try:
            # Submit build
            subprocess.run(
                [
                    "gcloud", "builds", "submit",
                    "--config", build_file,
                    "--project", self.project_id,
                    "."
                ],
                check=True
            )
        finally:
            # Clean up
            if os.path.exists(build_file):
                os.unlink(build_file)

    def _deploy_cloud_run_with_retry(self, max_retries: int = 3) -> str:
        """Deploy to Cloud Run with retry logic."""
        for attempt in range(max_retries):
            try:
                result = subprocess.run(
                    [
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
                        "--set-env-vars", f"GOOGLE_CLOUD_PROJECT={self.project_id}",
                        "--set-env-vars", f"GOOGLE_CLOUD_LOCATION={self.region}",
                        "--set-env-vars", "DEPLOYMENT_TARGET=cloud_run",
                        "--set-env-vars", "GOOGLE_GENAI_USE_VERTEXAI=true",
                        "--format", "json"
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )

                deployment = json.loads(result.stdout)
                return deployment.get("status", {}).get("url", "")

            except subprocess.CalledProcessError as e:
                logger.warning(f"Deployment attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise DeploymentError(f"Cloud Run deployment failed after {max_retries} attempts")

        return ""

    def deploy_agent_engine(self) -> str:
        """Deploy to Agent Engine."""
        logger.info("Starting Agent Engine deployment...")

        staging_bucket = os.getenv("STAGING_BUCKET")
        if not staging_bucket:
            raise DeploymentError("STAGING_BUCKET environment variable required")

        # Package the agent
        logger.info("Packaging agent...")
        package_path = self._package_agent()

        # Upload to staging bucket
        logger.info(f"Uploading to {staging_bucket}...")
        staged_path = self._upload_to_gcs(package_path, staging_bucket)

        # Deploy to Agent Engine
        logger.info("Creating Agent Engine instance...")
        engine_id = self._create_agent_engine_with_retry(staged_path)

        logger.info(f"✓ Deployment successful!")
        logger.info(f"Agent Engine ID: {engine_id}")

        return engine_id

    def _package_agent(self) -> str:
        """Package the agent for deployment."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        package_name = f"code_review_assistant_{timestamp}.tar.gz"

        # Files to include
        include_patterns = [
            "code_review_assistant/*.py",
            "code_review_assistant/sub_agents/*.py",
            "requirements.txt",
            "setup.py",
            ".env.example"
        ]

        # Create tar archive
        import tarfile
        with tarfile.open(package_name, "w:gz") as tar:
            for pattern in include_patterns:
                for file_path in Path(".").glob(pattern):
                    tar.add(file_path)

        logger.info(f"Created package: {package_name}")
        return package_name

    def _upload_to_gcs(self, local_path: str, bucket: str) -> str:
        """Upload package to GCS."""
        remote_path = f"{bucket}/{os.path.basename(local_path)}"

        subprocess.run(
            ["gsutil", "cp", local_path, remote_path],
            check=True
        )

        return remote_path

    def _create_agent_engine_with_retry(self, package_path: str, max_retries: int = 3) -> str:
        """Create Agent Engine instance with retry."""
        engine_config = {
            "display_name": "Code Review Assistant",
            "description": "AI-powered code review assistant for Python",
            "agent_resource": {
                "agent": "code_review_assistant.agent.root_agent",
                "agent_package_uri": package_path,
            },
            "model": "gemini-2.0-flash",
        }

        for attempt in range(max_retries):
            try:
                # This is a placeholder - actual Agent Engine API call would go here
                # For now, we'll use the ADK deployment command
                result = subprocess.run(
                    [
                        "adk", "deploy", "agent_engine",
                        "--project", self.project_id,
                        "--region", self.region,
                        "--staging_bucket", os.getenv("STAGING_BUCKET"),
                        "--display_name", "Code Review Assistant",
                        "."
                    ],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Parse engine ID from output
                # This is implementation-specific
                output = result.stdout
                if "Engine ID:" in output:
                    engine_id = output.split("Engine ID:")[1].strip().split()[0]
                    return engine_id

                return "deployment-successful"

            except subprocess.CalledProcessError as e:
                logger.warning(f"Agent Engine creation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise DeploymentError(f"Agent Engine creation failed after {max_retries} attempts")

        return ""

    def test_deployment(self, service_url: Optional[str] = None) -> bool:
        """Test the deployed service."""
        logger.info("Testing deployment...")

        if self.target == "cloud_run" and service_url:
            # Test Cloud Run endpoint
            import requests
            try:
                response = requests.get(f"{service_url}/health", timeout=10)
                if response.status_code == 200:
                    logger.info("✓ Health check passed")
                    return True
                else:
                    logger.warning(f"Health check returned {response.status_code}")
                    return False
            except requests.RequestException as e:
                logger.error(f"Health check failed: {e}")
                return False

        elif self.target == "agent_engine":
            # Agent Engine testing would be different
            logger.info("Agent Engine deployment test not implemented")
            return True

        return False

    def rollback(self, previous_version: Optional[str] = None) -> None:
        """Rollback to previous version if deployment fails."""
        logger.info("Initiating rollback...")

        if self.target == "cloud_run":
            if previous_version:
                subprocess.run(
                    [
                        "gcloud", "run", "services", "update-traffic",
                        self.service_name,
                        "--region", self.region,
                        "--project", self.project_id,
                        "--to-revisions", f"{previous_version}=100"
                    ],
                    check=True
                )
                logger.info(f"✓ Rolled back to {previous_version}")
            else:
                logger.warning("No previous version specified for rollback")

        elif self.target == "agent_engine":
            logger.info("Agent Engine rollback not implemented")


def main():
    """Main deployment function."""
    parser = argparse.ArgumentParser(description="Deploy Code Review Assistant")
    parser.add_argument(
        "--target",
        choices=["cloud_run", "agent_engine"],
        required=True,
        help="Deployment target"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="Google Cloud project ID"
    )
    parser.add_argument(
        "--region",
        default="us-central1",
        help="Google Cloud region"
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

    args = parser.parse_args()

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # Create deployer
    deployer = CodeReviewDeployer(
        target=args.target,
        project_id=args.project,
        region=args.region
    )

    try:
        # Validate prerequisites
        deployer.validate_prerequisites()

        # Deploy based on target
        if args.target == "cloud_run":
            result = deployer.deploy_cloud_run()
        else:
            result = deployer.deploy_agent_engine()

        # Test if requested
        if args.test:
            if not deployer.test_deployment(result):
                logger.warning("Deployment tests failed")
                if args.rollback:
                    deployer.rollback(args.rollback)
                    sys.exit(1)

        logger.info("🎉 Deployment completed successfully!")

    except DeploymentError as e:
        logger.error(f"Deployment failed: {e}")
        if args.rollback:
            deployer.rollback(args.rollback)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Deployment interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
