from kubiya_sdk.tools import Arg
from .base import AWSCliTool, GitHubRepolessCliTool
from kubiya_sdk.tools.registry import tool_registry

# Simplified IAM user creation with single group assignment
iam_create_user = AWSCliTool(
    name="iam_create_user",
    description="Create a new IAM user and add to a group",
    content="""
#!/bin/sh
set -e

echo "👤 Creating new IAM user: ${user_name}"

# Create the user
aws iam create-user --user-name "${user_name}"
echo "✅ User created successfully"

# Get group from environment variable
GROUP=${AWS_BACKEND_GROUP_NAME}
if [[ -z "$GROUP" ]]; then
    echo "❌ AWS_BACKEND_GROUP_NAME environment variable is not set"
    exit 1
fi

echo "👥 Adding user to IAM group: $GROUP"

# Add user to group
if aws iam add-user-to-group --user-name "${user_name}" --group-name "$GROUP"; then
    echo "✅ Successfully added ${user_name} to group $GROUP"
else
    echo "❌ Failed to add ${user_name} to group $GROUP"
    exit 1
fi

echo "✅ IAM user ${user_name} setup complete"
""",
    args=[
        Arg(name="user_name", type="str", description="Name of the IAM user to create", required=True),
    ],
)

# Add user to GitHub using email and add to a team
github_add_user = GitHubRepolessCliTool(
    name="github_add_user",
    description="Invite a user to a GitHub organization using their email address and add to a team",
    content="""
#!/bin/sh
set -e

# Get organization from environment variable
ORGANIZATION=${GH_ORG}
if [[ -z "$ORGANIZATION" ]]; then
    echo "❌ GH_ORG environment variable is not set"
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

echo "👤 Inviting user to GitHub organization..."
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
else
    echo "❌ Failed to send organization invitation"
    echo "📄 Request payload was:"
    cat /tmp/invite.json
    exit 1
fi
""",
    args=[
        Arg(name="email", type="str", description="Email address of the user to invite to the organization", required=True),
        Arg(name="team_type", type="str", description="Type of team to add the user to ('frontend' or 'backend')", required=True),
    ],
)

# Register all developer onboarding tools
for tool in [iam_create_user, github_add_user]:
    tool_registry.register("developer_onboarding", tool)

# Export all developer onboarding tools
__all__ = ['iam_create_user', 'github_add_user']
