from kubiya_sdk.tools import Tool, Arg
from .common import COMMON_ENV, COMMON_FILES, COMMON_SECRETS

GITHUB_ICON_URL = "https://cdn-icons-png.flaticon.com/256/25/25231.png"
GITHUB_CLI_DOCKER_IMAGE = "maniator/gh:latest"
AWS_ICON_URL = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/93/Amazon_Web_Services_Logo.svg/2560px-Amazon_Web_Services_Logo.svg.png"

class GitHubRepolessCliTool(Tool):
    def __init__(self, name, description, content, args, long_running=False):
        enhanced_content = f"""
#!/bin/sh
set -e

if ! command -v jq >/dev/null 2>&1; then
    # Silently install jq (TODO:: install git as well for git operations)
    apk add --quiet jq >/dev/null 2>&1
fi

check_and_set_org() {{
    if [ -n "$org" ]; then
        echo "Using organization: $org"
    else
        orgs=$(gh api user/orgs --jq '.[].login')
        org_count=$(echo "$orgs" | wc -l)
        if [ "$org_count" -eq 0 ]; then
            echo "You are not part of any organization."
        elif [ "$org_count" -eq 1 ]; then
            org=$orgs
            echo "You are part of one organization: $org. Using this organization."
        else
            echo "You are part of the following organizations:"
            echo "$orgs"
            echo "Please specify the organization in your command if needed."
        fi
    fi
}}
check_and_set_org

{content}
"""

        updated_args = [arg for arg in args if arg.name not in ["org", "repo"]]
        updated_args.extend([
            Arg(name="org", type="str", description="GitHub organization name. If you're a member of only one org, it will be used automatically.", required=False),
        ])

        super().__init__(
            name=name,
            description=description,
            icon_url=GITHUB_ICON_URL,
            type="docker",
            image=GITHUB_CLI_DOCKER_IMAGE,
            content=enhanced_content,
            args=updated_args,
            env=COMMON_ENV,
            files=COMMON_FILES,
            secrets=COMMON_SECRETS,
            long_running=long_running
        )

class AWSCliTool(Tool):
    def __init__(self, name, description, content, args, long_running=False, mermaid_diagram=None):
        super().__init__(
            name=name,
            description=description,
            icon_url=AWS_ICON_URL,
            type="docker",
            image="amazon/aws-cli:latest",
            content=content,
            args=args,
            with_files=COMMON_FILES,
            env=COMMON_ENV,
            long_running=long_running,
            mermaid_diagram=mermaid_diagram
        )

class CombinedAWSGitHubTool(Tool):
    def __init__(self, name, description, content, args, long_running=False, mermaid_diagram=None):
        enhanced_content = f"""
#!/bin/sh
set -e

# Install AWS CLI v2 and GitHub CLI in the GitHub CLI image
echo "Installing AWS CLI..."
apk add --no-cache python3 py3-pip curl unzip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip -q awscliv2.zip
./aws/install
rm -rf awscliv2.zip aws/

# Install jq if not available
if ! command -v jq >/dev/null 2>&1; then
    apk add --quiet jq >/dev/null 2>&1
fi

# GitHub organization check function
check_and_set_org() {{
    if [ -n "$org" ]; then
        echo "Using organization: $org"
    else
        orgs=$(gh api user/orgs --jq '.[].login')
        org_count=$(echo "$orgs" | wc -l)
        if [ "$org_count" -eq 0 ]; then
            echo "You are not part of any organization."
        elif [ "$org_count" -eq 1 ]; then
            org=$orgs
            echo "You are part of one organization: $org. Using this organization."
        else
            echo "You are part of the following organizations:"
            echo "$orgs"
            echo "Please specify the organization in your command if needed."
        fi
    fi
}}

{content}
"""

        # Add org parameter for GitHub functionality
        updated_args = [arg for arg in args if arg.name != "org"]
        updated_args.append(
            Arg(name="org", type="str", description="GitHub organization name. If you're a member of only one org, it will be used automatically.", required=False)
        )

        super().__init__(
            name=name,
            description=description,
            icon_url=AWS_ICON_URL,
            type="docker",
            image=GITHUB_CLI_DOCKER_IMAGE,  # Use the existing GitHub CLI image and install AWS CLI
            content=enhanced_content,
            args=updated_args,
            env=COMMON_ENV,
            files=COMMON_FILES,
            secrets=COMMON_SECRETS,
            long_running=long_running,
            mermaid_diagram=mermaid_diagram
        )