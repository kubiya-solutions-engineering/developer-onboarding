from kubiya_sdk.tools.models import FileSpec

# Make sure you enable AWS integration on the Kubiya platform and that the TeamMate which is running this has the correct permissions to access AWS (is using an integration with AWS)
COMMON_FILES = [
    FileSpec(source="$HOME/.aws/credentials", destination="/root/.aws/credentials"),
    FileSpec(source="$HOME/.aws/config", destination="/root/.aws/config"),
]


COMMON_ENV = [
    "AWS_PROFILE",
    "GH_ORG",
    "GH_FRONTEND_TEAM",
    "GH_BACKEND_TEAM",
    "AWS_BACKEND_GROUP_NAME"
    ]

COMMON_SECRETS = [
    "GH_TOKEN_ONBOARDING", # Github Token (integration) - https://docs.kubiya.ai/integrations/github
]