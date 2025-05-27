from kubiya_sdk.tools import Arg
from .base import CombinedAWSGitHubTool
from kubiya_sdk.tools.registry import tool_registry

# Combined developer onboarding tool
onboard_developer_iam_github_create = CombinedAWSGitHubTool(
    name="onboard_developer_iam_github_create",
    description="Onboard a new developer by creating an IAM user in AWS and inviting them to GitHub organization with team assignment",
    content="""
#!/bin/sh
set -e

echo "🚀 Starting combined AWS and GitHub developer onboarding process"
echo "👤 User: ${user_name}"
echo "📧 Email: ${email}"

# =============================================================================
# AWS IAM User Creation
# =============================================================================
echo ""
echo "🔧 AWS IAM Setup"
echo "=================="

echo "👤 Creating new IAM user: ${user_name}"

# Create the user
if aws iam create-user --user-name "${user_name}"; then
    echo "✅ AWS IAM user created successfully"
else
    echo "❌ Failed to create AWS IAM user"
    exit 1
fi

# Get group from environment variable
AWS_GROUP=${AWS_BACKEND_GROUP_NAME}
if [[ -z "$AWS_GROUP" ]]; then
    echo "❌ AWS_BACKEND_GROUP_NAME environment variable is not set"
    exit 1
fi

echo "👥 Adding user to IAM group: $AWS_GROUP"

# Add user to group
if aws iam add-user-to-group --user-name "${user_name}" --group-name "$AWS_GROUP"; then
    echo "✅ Successfully added ${user_name} to AWS group $AWS_GROUP"
else
    echo "❌ Failed to add ${user_name} to AWS group $AWS_GROUP"
    exit 1
fi

# =============================================================================
# GitHub Organization Invitation
# =============================================================================
echo ""
echo "🐙 GitHub Setup"
echo "================"

# Run the org check function
check_and_set_org

# Get organization from environment variable or the org check
ORGANIZATION=${GH_ORG:-$org}
if [[ -z "$ORGANIZATION" ]]; then
    echo "❌ GH_ORG environment variable is not set and no organization detected"
    exit 1
fi

# Get team based on team_type
if [[ "${team_type}" == "frontend" ]]; then
    TEAM=${GH_FRONTEND_TEAM}
    if [[ -z "$TEAM" ]]; then
        echo "❌ GH_FRONTEND_TEAM environment variable is not set"
        exit 1
    fi
elif [[ "${team_type}" == "backend" ]]; then
    TEAM=${GH_BACKEND_TEAM}
    if [[ -z "$TEAM" ]]; then
        echo "❌ GH_BACKEND_TEAM environment variable is not set"
        exit 1
    fi
else
    echo "❌ Invalid team_type: ${team_type}. Must be 'frontend' or 'backend'"
    exit 1
fi

echo "👤 Inviting developer to GitHub organization..."
echo "📧 Email: ${email}"
echo "🏢 Organization: $ORGANIZATION"
echo "👥 Team: $TEAM"

# Get team ID - fully dynamic approach
echo "🔍 Looking up team ID for '$TEAM'..."

# Convert team name to lowercase for slug comparison
TEAM_SLUG=$(echo "$TEAM" | tr '[:upper:]' '[:lower:]')
echo "🔍 Looking up team by slug: $TEAM_SLUG"

# Try to get team directly by slug (most reliable method)
TEAM_RESPONSE=$(gh api "orgs/$ORGANIZATION/teams/$TEAM_SLUG" 2>/dev/null || echo "")

if [[ ! -z "$TEAM_RESPONSE" ]]; then
    TEAM_ID=$(echo "$TEAM_RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    echo "✅ Found team ID via direct slug lookup: $TEAM_ID"
else
    echo "⚠️ Team not found by slug, trying alternative methods..."
    # List all teams and find the one we want
    gh api "orgs/$ORGANIZATION/teams" > /tmp/teams.json
    
    # Try case-insensitive name match
    TEAM_ID=$(cat /tmp/teams.json | grep -i "\"name\":\"$TEAM\"" -B 2 | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    
    if [[ -z "$TEAM_ID" ]]; then
        # Try case-insensitive slug match
        TEAM_ID=$(cat /tmp/teams.json | grep -i "\"slug\":\"$TEAM_SLUG\"" -B 5 | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
    fi
fi

if [[ -z "$TEAM_ID" ]]; then
    echo "❌ Team '$TEAM' not found in organization '$ORGANIZATION'"
    echo "💡 Please check the team name and make sure it exists in the organization"
    exit 1
fi

echo "✅ Found team ID: $TEAM_ID"

# Send invitation to the email address with team assignment
echo "📤 Sending invitation to ${email} for team ID: $TEAM_ID"

# Create a properly quoted JSON file with valid role value
cat > /tmp/invite.json << EOF
{
  "email": "${email}",
  "role": "direct_member",
  "team_ids": [${TEAM_ID}]
}
EOF

echo "📄 Using request payload:"
cat /tmp/invite.json

# Send the invitation using the GitHub CLI with the input file
if gh api --method POST "orgs/$ORGANIZATION/invitations" --input /tmp/invite.json; then
    echo "✅ Successfully sent organization invitation to ${email}"
    echo "👥 User will be added to team '$TEAM' upon accepting the invitation"
    echo "📧 The user will receive an email to accept the invitation"
    echo "🔗 You can check pending invitations at: https://github.com/orgs/$ORGANIZATION/people/pending_invitations"
    echo ""
    echo "🎉 Combined AWS and GitHub developer onboarding complete!"
    echo "📋 Summary:"
    echo "   - AWS IAM user '${user_name}' created and added to group '$AWS_GROUP'"
    echo "   - GitHub invitation sent to '${email}' for team '$TEAM'"
else
    echo "❌ Failed to send organization invitation"
    echo "📄 Request payload was:"
    cat /tmp/invite.json
    exit 1
fi
""",
    args=[
        Arg(name="user_name", type="str", description="Name of the IAM user to create", required=True),
        Arg(name="email", type="str", description="Email address of the user to invite to the GitHub organization", required=True),
        Arg(name="team_type", type="str", description="Type of team to add the user to ('frontend' or 'backend')", required=True),
    ],
)

# Register the combined tool
tool_registry.register("developer_onboarding", combined_onboard_developer)

# Export the combined tool
__all__ = ['combined_onboard_developer']
