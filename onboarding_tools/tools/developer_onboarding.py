from kubiya_sdk.tools import Arg
from .base import CombinedAWSGitHubTool
from kubiya_sdk.tools.registry import tool_registry

# Combined developer onboarding tool with better naming and description
onboard_to_team = CombinedAWSGitHubTool(
    name="onboard_to_team",
    description="Onboard and invite a new developer to frontend team (GitHub only) or backend team (GitHub + AWS IAM). Creates AWS IAM user for backend developers and sends GitHub organization invitation with team assignment.",
    content="""
#!/bin/sh
set -e

echo "🚀 Starting combined AWS and GitHub developer onboarding process"
echo "📧 Email: ${email}"
echo "👥 Team Type: ${team_type}"

# Extract username from email (everything before @)
user_name=$(echo "${email}" | cut -d'@' -f1)
echo "👤 Derived AWS username: ${user_name}"

# Track success/failure status
AWS_SUCCESS=false
GITHUB_SUCCESS=false

# =============================================================================
# AWS IAM User Creation (Backend Only)
# =============================================================================
if [[ "${team_type}" == "backend" ]]; then
    echo ""
    echo "🔧 AWS IAM Setup (Backend Team)"
    echo "================================"

    echo "👤 Creating new IAM user: ${user_name}"

    # Create the user
    if aws iam create-user --user-name "${user_name}" >/dev/null 2>&1; then
        echo "✅ AWS IAM user created successfully"
        
        # Get group from environment variable
        AWS_GROUP=${AWS_BACKEND_GROUP_NAME}
        if [[ -z "$AWS_GROUP" ]]; then
            echo "❌ AWS_BACKEND_GROUP_NAME environment variable is not set"
        else
            echo "👥 Adding user to IAM group: $AWS_GROUP"

            # Add user to group
            if aws iam add-user-to-group --user-name "${user_name}" --group-name "$AWS_GROUP" >/dev/null 2>&1; then
                echo "✅ Successfully added ${user_name} to AWS group $AWS_GROUP"
                AWS_SUCCESS=true
            else
                echo "❌ Failed to add ${user_name} to AWS group $AWS_GROUP"
                # Show the actual error
                aws iam add-user-to-group --user-name "${user_name}" --group-name "$AWS_GROUP" 2>&1 || true
                echo "⚠️  AWS user created but group assignment failed. Continuing with GitHub setup..."
            fi
        fi
    else
        echo "❌ Failed to create AWS IAM user"
        # Show the actual error
        ERROR_MSG=$(aws iam create-user --user-name "${user_name}" 2>&1 || true)
        echo "$ERROR_MSG"
        
        # Check if user already exists
        if echo "$ERROR_MSG" | grep -q "EntityAlreadyExists"; then
            echo "ℹ️  User already exists. Checking group membership..."
            
            # Get group from environment variable
            AWS_GROUP=${AWS_BACKEND_GROUP_NAME}
            if [[ ! -z "$AWS_GROUP" ]]; then
                # Check if user is already in the group
                if aws iam list-groups-for-user --user-name "${user_name}" --query "Groups[?GroupName=='$AWS_GROUP'].GroupName" --output text | grep -q "$AWS_GROUP"; then
                    echo "✅ User ${user_name} is already in group $AWS_GROUP"
                    AWS_SUCCESS=true
                else
                    echo "👥 Adding existing user to IAM group: $AWS_GROUP"
                    if aws iam add-user-to-group --user-name "${user_name}" --group-name "$AWS_GROUP" >/dev/null 2>&1; then
                        echo "✅ Successfully added existing user ${user_name} to AWS group $AWS_GROUP"
                        AWS_SUCCESS=true
                    else
                        echo "❌ Failed to add existing user ${user_name} to AWS group $AWS_GROUP"
                        aws iam add-user-to-group --user-name "${user_name}" --group-name "$AWS_GROUP" 2>&1 || true
                    fi
                fi
            fi
        fi
        
        if [[ "$AWS_SUCCESS" != "true" ]]; then
            echo "⚠️  AWS setup failed. Continuing with GitHub setup..."
        fi
    fi
else
    echo ""
    echo "ℹ️  Skipping AWS IAM Setup (Frontend Team - GitHub only)"
    AWS_SUCCESS=true  # Not applicable for frontend
fi

# =============================================================================
# GitHub Organization Invitation (Both Teams)
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
    echo "⚠️  GitHub setup failed"
else
    # Get team based on team_type
    if [[ "${team_type}" == "frontend" ]]; then
        TEAM=${GH_FRONTEND_TEAM}
        if [[ -z "$TEAM" ]]; then
            echo "❌ GH_FRONTEND_TEAM environment variable is not set"
            echo "⚠️  GitHub setup failed"
        fi
    elif [[ "${team_type}" == "backend" ]]; then
        TEAM=${GH_BACKEND_TEAM}
        if [[ -z "$TEAM" ]]; then
            echo "❌ GH_BACKEND_TEAM environment variable is not set"
            echo "⚠️  GitHub setup failed"
        fi
    else
        echo "❌ Invalid team_type: ${team_type}. Must be 'frontend' or 'backend'"
        echo "⚠️  GitHub setup failed"
        TEAM=""
    fi

    if [[ ! -z "$TEAM" ]]; then
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
            echo "📋 Available teams:"
            cat /tmp/teams.json | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | sort
            echo "⚠️  GitHub setup failed"
        else
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
            if gh api --method POST "orgs/$ORGANIZATION/invitations" --input /tmp/invite.json >/dev/null 2>&1; then
                echo "✅ Successfully sent organization invitation to ${email}"
                echo "👥 User will be added to team '$TEAM' upon accepting the invitation"
                echo "📧 The user will receive an email to accept the invitation"
                echo "🔗 You can check pending invitations at: https://github.com/orgs/$ORGANIZATION/people/pending_invitations"
                GITHUB_SUCCESS=true
            else
                echo "❌ Failed to send organization invitation"
                echo "📄 Request payload was:"
                cat /tmp/invite.json
                echo "🔍 Error details:"
                gh api --method POST "orgs/$ORGANIZATION/invitations" --input /tmp/invite.json 2>&1 || true
                echo "⚠️  GitHub setup failed"
            fi
        fi
    fi
fi

# =============================================================================
# Final Summary
# =============================================================================
echo ""
echo "📋 Onboarding Summary"
echo "====================="

if [[ "${team_type}" == "backend" ]]; then
    if [[ "$AWS_SUCCESS" == "true" ]]; then
        echo "✅ AWS IAM: User '${user_name}' successfully configured"
    else
        echo "❌ AWS IAM: Setup failed"
    fi
fi

if [[ "$GITHUB_SUCCESS" == "true" ]]; then
    echo "✅ GitHub: Invitation sent to '${email}'"
else
    echo "❌ GitHub: Invitation failed"
fi

# Determine overall success
if [[ "${team_type}" == "frontend" ]]; then
    # Frontend only needs GitHub
    if [[ "$GITHUB_SUCCESS" == "true" ]]; then
        echo ""
        echo "🎉 Frontend developer onboarding completed successfully!"
        exit 0
    else
        echo ""
        echo "💥 Frontend developer onboarding failed"
        exit 1
    fi
else
    # Backend needs both AWS and GitHub
    if [[ "$AWS_SUCCESS" == "true" && "$GITHUB_SUCCESS" == "true" ]]; then
        echo ""
        echo "🎉 Backend developer onboarding completed successfully!"
        exit 0
    elif [[ "$GITHUB_SUCCESS" == "true" ]]; then
        echo ""
        echo "⚠️  Backend developer onboarding partially completed (GitHub only)"
        echo "💡 Please manually configure AWS access for the user"
        exit 0
    else
        echo ""
        echo "💥 Backend developer onboarding failed"
        exit 1
    fi
fi
""",
    args=[
        Arg(name="email", type="str", description="Email address of the developer to onboard and invite to the GitHub organization", required=True),
        Arg(name="team_type", type="str", description="Team type for onboarding: 'frontend' (GitHub only) or 'backend' (GitHub + AWS IAM)", required=True),
    ],
)

# Register the single combined tool
tool_registry.register("developer_onboarding", onboard_to_team)

# Export the single tool
__all__ = ['onboard_to_team']
