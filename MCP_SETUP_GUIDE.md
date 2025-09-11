# MCP Servers Setup Guide

This guide sets up three MCP (Model Context Protocol) servers to extend AI assistants with
Grafana, GitHub, and PagerDuty integrations. Supports both **VSCode GitHub Copilot** and **Claude Code**.

## Choose Your AI Assistant

- **[VSCode GitHub Copilot](#vscode-github-copilot-setup)**: For VSCode users with GitHub Copilot extension
- **[Claude Code](#claude-code-setup)**: For Anthropic's Claude Code CLI users

## VSCode GitHub Copilot Setup

### 🚀 VSCode Quick Start (5 Minutes)

1. **Enable MCP**: VSCode Settings → Search "copilot mcp" → Check "Enable MCP"
2. **Install tools**:
   - Pull Docker image for Grafana: `docker pull mcp/grafana`
   - Install uvx for PagerDuty: `pip install uvx`
3. **Start services**: `make up` (starts your local Grafana)
4. **Get tokens**: Create GitHub Personal Access Token + Grafana service account token +
   PagerDuty User API token
5. **Restart VSCode**: Enter tokens when prompted

**That's it!** Skip to [Testing Your VSCode Setup](#testing-your-vscode-setup) to verify everything works.

---

## 📋 Detailed Setup Checklist

- [ ] VSCode 1.101+ with GitHub Copilot extension
- [ ] Enable MCP in VSCode settings
- [ ] Install required tools (Docker)
- [ ] Configure authentication for each service
- [ ] Test server connections

## Prerequisites

### Required Software

1. **VSCode 1.101 or later** with GitHub Copilot extension installed
2. **Docker**: Required for Grafana MCP server
3. **Python 3.8+** with **uvx** (or pipx): Required for PagerDuty MCP server

### Enable MCP in VSCode

1. Open VSCode Settings (`Cmd/Ctrl + ,`)
2. Search for "copilot mcp"
3. Check "GitHub Copilot › Chat: Enable MCP"

## Server Configuration

The configuration is already set up in `.vscode/mcp.json`. Here's what each server provides:

### 1. GitHub MCP Server (Remote HTTP)

- **Status**: ⏳ Requires authentication setup
- **Type**: Remote HTTP MCP server hosted by GitHub
- **URL**: <https://api.githubcopilot.com/mcp/>
- **Capabilities**: Repository management, GitHub Actions, code security, issues/PRs
- **Authentication**: GitHub Personal Access Token required

### 2. Grafana MCP Server

- **Status**: ⏳ Requires Docker services running + authentication setup
- **Capabilities**: Dashboard management, metrics queries, alert rules
- **URL**: Pre-configured for local Docker instance (<http://localhost:3000>)
- **Authentication**: Service Account Token required

### 3. PagerDuty MCP Server (Local)

- **Status**: ⏳ Requires authentication setup
- **Type**: Local MCP server using uvx/pipx
- **Command**: `uvx pagerduty-mcp --enable-write-tools`
- **Capabilities**: Incident management, on-call schedules, escalation policies
- **Authentication**: User API Token required

## Authentication Setup

### GitHub Authentication

#### Step 1: Create GitHub Personal Access Token

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **"Generate new token (classic)"**
3. Enter description: `VSCode MCP Integration`
4. Select scopes:
   - `repo` (Full control of private repositories)
   - `read:org` (Read org and team membership)
   - `read:user` (Read user profile data)
   - `workflow` (Update GitHub Action workflows)
5. Click **"Generate token"**
6. **Copy and save the token securely** (you won't see it again)

#### Step 2: Test Remote GitHub MCP Connection

The GitHub MCP server is hosted remotely by GitHub at `https://api.githubcopilot.com/mcp/`.
No local installation is required - VSCode will connect directly to the remote server using your
Personal Access Token.

### Grafana Authentication

#### Step 1: Start Your Docker Services

First, ensure your local Grafana instance is running:

```bash
# Start all services including Grafana
make up

# Or use docker-compose directly
docker-compose up -d

# Verify Grafana is running
curl http://localhost:3000/api/health
```

Your Grafana instance should be accessible at <http://localhost:3000> with default credentials `admin/admin`.

#### Step 2: Pull Grafana MCP Server Docker Image

The configuration is set to use Docker, so simply pull the image:

```bash
docker pull mcp/grafana
```

**Note:** The MCP server will automatically run in a Docker container when needed.
No binary installation required!

#### Step 3: Create Service Account Token

1. Open your local Grafana instance at <http://localhost:3000>
2. Log in with default credentials: `admin/admin` (change password when prompted)
3. Navigate to **Administration** → **Service Accounts**
4. Click **Add Service Account**
5. Enter name: `MCP Server` (or any descriptive name)
6. Set role: **Editor** or **Admin** (depending on required permissions)
7. Click **Add**
8. Click **Add Service Account Token**
9. Enter description: `VSCode MCP Integration`
10. **Copy and save the token securely** (you won't see it again)

#### Step 4: Test Grafana MCP Server

```bash
# Test the Docker image is available
docker images mcp/grafana

# Test connection (replace with your token)
docker run --rm -i --network=host \
  -e GRAFANA_URL="http://localhost:3000" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="your-token" \
  mcp/grafana -t stdio
```

### PagerDuty Authentication

#### Step 1: Create PagerDuty API Token

1. Log into your PagerDuty account
2. Go to **User Settings** (click your profile picture → **My Profile**)
3. Select **User API Tokens** tab
4. Click **Create API Token**
5. Enter description: `VSCode MCP Integration`
6. **Copy and save the token securely**

#### Step 2: Install and Test Local PagerDuty MCP Server

The PagerDuty MCP server runs locally using uvx (or pipx). First, ensure you have uvx installed:

```bash
# Install uvx if not already installed
pip install uvx

# Test the PagerDuty MCP server installation
uvx pagerduty-mcp --help

# Test with your API key (replace with your actual token)
PAGERDUTY_USER_API_KEY="your-token" uvx pagerduty-mcp --enable-write-tools
```

**Note:** The server will be automatically started by VSCode when needed using the configuration in `.vscode/mcp.json`.

## Activating the Servers

### Start MCP Servers

1. **Restart VSCode** or run the command:
   - Open Command Palette (`Cmd/Ctrl + Shift + P`)
   - Run **"MCP: Restart Servers"**

2. **Enter credentials when prompted**:
   - VSCode will prompt for your Grafana service account token
   - VSCode will prompt for your PagerDuty API token

### Verify Server Status

1. Open **Output** panel (`View` → **Output**)
2. Select **"MCP"** from the dropdown
3. Look for successful connection messages:

   ```text
   [INFO] GitHub MCP server connected
   [INFO] Grafana MCP server connected
   [INFO] PagerDuty MCP server connected
   ```

## Testing Your VSCode Setup

### Test GitHub MCP

Open GitHub Copilot Chat and try:

```text
Show me the recent issues in this repository
What GitHub Actions are configured for this project?
```

### Test Grafana MCP

```text
Show me the available dashboards in Grafana
What are the current alerts in my Grafana instance?
```

### Test PagerDuty MCP

```text
Show me active incidents in PagerDuty
Who is currently on call?
```

## Troubleshooting

### Common Issues

#### "Server failed to start"

1. Check the **Output** panel (View → Output → MCP)
2. Verify Docker images are available for local services:

   ```bash
   docker images mcp/grafana
   ```

3. Test remote server connectivity and authentication

#### "Authentication failed"

1. **GitHub**: Verify Personal Access Token has correct scopes and is not expired
2. **Grafana**: Verify service account token has correct permissions
3. **PagerDuty**: Verify API token is a User API Token (not Integration Key)
4. Re-enter credentials in VSCode input prompts

#### "Docker image not found"

```bash
# Pull the Grafana MCP Docker image
docker pull mcp/grafana

# Verify the image is available
docker images mcp/grafana
```

#### "Remote MCP connection failed"

For GitHub remote MCP server connection issues:

1. **GitHub**: Check connectivity to <https://api.githubcopilot.com/mcp/> and verify token permissions
2. Verify internet connectivity and firewall settings
3. Review VSCode Output panel for detailed error messages

#### "Local MCP server failed"

For PagerDuty local MCP server issues:

1. **uvx/pipx**: Verify uvx is installed: `pip install uvx`
2. **PagerDuty package**: Test installation: `uvx pagerduty-mcp --help`
3. **API token**: Verify token has correct permissions in PagerDuty
4. **Python environment**: Check Python version compatibility (3.8+)

### Debug Steps

1. **Check server logs**: View → Output → MCP
2. **Restart servers**: Command Palette → "MCP: Restart Servers"
3. **Test individual components**:

   ```bash
   # Test Grafana MCP (Docker)
   docker run --rm -i --network=host \
     -e GRAFANA_URL="http://localhost:3000" \
     -e GRAFANA_SERVICE_ACCOUNT_TOKEN="your-token" \
     mcp/grafana --help

   # Test PagerDuty MCP (Local uvx)
   PAGERDUTY_USER_API_KEY="your-token" uvx pagerduty-mcp --enable-write-tools

   # Test remote MCP connections (GitHub)
   # GitHub connection is handled automatically by VSCode using remote HTTP server
   # Check VSCode Output panel for connection status
   ```

### Re-entering Credentials

If you need to update your API tokens:

1. Command Palette (`Cmd/Ctrl + Shift + P`)
2. Run **"MCP: Reset Input Values"**
3. Run **"MCP: Restart Servers"**
4. Enter new credentials when prompted

## Security Best Practices

1. **Token Management**
   - Use service accounts with minimal required permissions
   - Rotate tokens regularly according to your organization's policy
   - Never commit tokens to version control

2. **Network Security**
   - Use HTTPS for all Grafana connections
   - Consider network restrictions for API access
   - Monitor API token usage in your services

3. **Access Control**
   - Grant minimal permissions needed for intended use cases
   - Review and audit token permissions regularly
   - Use separate tokens for different purposes

## Advanced Configuration

### Custom Grafana Configuration

To use different Grafana transport modes or additional flags:

```json
{
  "servers": {
    "grafana-mcp": {
      "type": "stdio",
      "command": "mcp-grafana",
      "args": [
        "--transport", "stdio",
        "--disable-alerts",
        "--disable-folders"
      ],
      "env": {
        "GRAFANA_URL": "${input:grafanaUrl}",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN": "${input:grafanaToken}"
      }
    }
  }
}
```

### Using Local GitHub MCP Server

If you prefer running GitHub MCP locally:

1. Install Docker
2. Update `.vscode/mcp.json`:

```json
{
  "servers": {
    "github-mcp": {
      "type": "stdio",
      "command": "docker",
      "args": ["run", "--rm", "-i", "github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "${input:githubToken}"
      }
    }
  }
}
```

## Available Tools by Server

### GitHub MCP Server (Remote HTTP)

- Repository information and statistics
- Issue and pull request management
- GitHub Actions workflow data
- Code security scanning results
- Branch and commit information
- **Note**: Hosted remotely by GitHub at <https://api.githubcopilot.com/mcp/>

### Grafana MCP Server

- Dashboard listing and queries
- Panel data retrieval
- Alert rule management
- Data source queries
- Annotation management

### PagerDuty MCP Server (Local)

- Incident creation and management
- On-call schedule queries
- Service and escalation policy information
- Integration management
- Analytics and reporting data
- **Note**: Runs locally using `uvx pagerduty-mcp --enable-write-tools`

---

## Claude Code Setup

### 🚀 Claude Code Quick Start (5 Minutes)

1. **Install Claude Code**: Follow [installation instructions](https://docs.anthropic.com/en/docs/claude-code/getting-started)
2. **Install tools**:
   - Pull Docker image for Grafana: `docker pull mcp/grafana`
   - Install uvx for PagerDuty: `pip install uvx`
3. **Start services**: `make up` (starts your local Grafana)
4. **Get tokens**: Create GitHub Personal Access Token + Grafana service account token +
   PagerDuty User API token
5. **Configure MCP servers**: Use `claude mcp add` commands (see below)

**That's it!** Skip to [Testing Your Claude Code Setup](#testing-your-claude-code-setup)
to verify everything works.

---

## 📋 Detailed Claude Code Setup

### Claude Code Prerequisites

1. **Claude Code CLI**: Install from [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code)
2. **Docker**: Required for Grafana MCP server
3. **Python 3.8+** with **uvx** (or pipx): Required for PagerDuty MCP server

### Server Configuration Options

Claude Code supports three types of MCP server connections:

#### 1. **Local stdio server** (Recommended for PagerDuty)

- Runs as local process with direct system access
- Best for tools needing file system or local API access

#### 2. **Remote HTTP server** (Recommended for GitHub)

- Uses standard request/response patterns
- Best for hosted services with REST APIs

#### 3. **Remote SSE server** (Advanced)

- Server-Sent Events for real-time streaming
- Best for real-time data feeds

### Configuration Scopes

- **Local** (default): Private to current project directory
- **Project**: Shared via `.mcp.json` file (recommended)
- **User**: Available across all projects

## MCP Server Setup Commands

### Method 1: Project-Level Configuration (Recommended)

Create a `.mcp.json` file in your project root for team sharing (example provided in this repository):

```json
{
  "mcpServers": {
    "github-mcp": {
      "command": "claude",
      "args": ["mcp", "proxy"],
      "env": {
        "MCP_SERVER_URL": "https://api.githubcopilot.com/mcp/",
        "GITHUB_TOKEN": "your-github-token-here"
      }
    },
    "grafana-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i", "--network=host",
        "-e", "GRAFANA_URL=http://localhost:3000",
        "-e", "GRAFANA_SERVICE_ACCOUNT_TOKEN=your-grafana-token-here",
        "mcp/grafana"
      ]
    },
    "pagerduty-mcp": {
      "command": "uvx",
      "args": ["pagerduty-mcp", "--enable-write-tools"],
      "env": {
        "PAGERDUTY_USER_API_KEY": "your-pagerduty-token-here"
      }
    }
  }
}
```

### Method 2: Command Line Configuration

Add servers individually using Claude Code CLI:

#### Claude Code GitHub MCP Server (Remote HTTP)

```bash
# Add GitHub MCP server (remote hosted by GitHub)
claude mcp add github-mcp --transport http https://api.githubcopilot.com/mcp/ \
  --env GITHUB_TOKEN="your-github-token-here"
```

#### Claude Code Grafana MCP Server (Docker)

```bash
# Add Grafana MCP server (local Docker container)
claude mcp add grafana-mcp docker run --rm -i --network=host mcp/grafana \
  --env GRAFANA_URL="http://localhost:3000" \
  --env GRAFANA_SERVICE_ACCOUNT_TOKEN="your-grafana-token-here"
```

#### Claude Code PagerDuty MCP Server (Local)

```bash
# Add PagerDuty MCP server (local uvx/pipx)
claude mcp add pagerduty-mcp uvx pagerduty-mcp --enable-write-tools \
  --env PAGERDUTY_USER_API_KEY="your-pagerduty-token-here"
```

## Claude Code Authentication Setup

### Claude Code GitHub Authentication

Follow the same steps as VSCode setup:

1. Go to GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click **"Generate new token (classic)"**
3. Enter description: `Claude Code MCP Integration`
4. Select scopes: `repo`, `read:org`, `read:user`, `workflow`
5. **Copy and save the token securely**

### Claude Code Grafana Authentication

Follow the same steps as VSCode setup:

1. Start services: `make up`
2. Pull Docker image: `docker pull mcp/grafana`
3. Open Grafana at <http://localhost:3000> (admin/admin)
4. Create Service Account with **Editor** or **Admin** role
5. Generate Service Account Token
6. **Copy and save the token securely**

### Claude Code PagerDuty Authentication

Follow the same steps as VSCode setup:

1. Go to **User Settings** → **User API Tokens**
2. Create API Token with description: `Claude Code MCP Integration`
3. **Copy and save the token securely**

## Managing MCP Servers

### List configured servers

```bash
claude mcp list
```

### Get server details

```bash
claude mcp get github-mcp
```

### Remove a server

```bash
claude mcp remove github-mcp
```

### Update server configuration

```bash
# Remove old configuration
claude mcp remove server-name

# Add new configuration
claude mcp add server-name [new-config...]
```

## Testing Your Claude Code Setup

### Verify Claude Code Server Status

```bash
# List all configured servers
claude mcp list

# Check specific server status
claude mcp get github-mcp
claude mcp get grafana-mcp
claude mcp get pagerduty-mcp
```

### Test MCP Integration

Open Claude Code and try these queries:

#### Test Claude Code GitHub MCP

```text
Show me the recent issues in this repository
What GitHub Actions are configured for this project?
List the recent commits on the main branch
```

#### Test Claude Code Grafana MCP

```text
Show me the available dashboards in Grafana
What are the current alerts in my Grafana instance?
Query the latest metrics from my application
```

#### Test Claude Code PagerDuty MCP

```text
Show me active incidents in PagerDuty
Who is currently on call?
Create a test incident for validation
```

## Troubleshooting Claude Code

### Claude Code Common Issues

#### "Server not found"

```bash
# Check if server is configured
claude mcp list

# Re-add the server if missing
claude mcp add server-name [config...]
```

#### Claude Code "Authentication failed"

1. Verify tokens are not expired
2. Check token permissions match requirements
3. Update environment variables in `.mcp.json` or re-add server

#### Claude Code "Docker image not found"

```bash
# Pull required Docker images
docker pull mcp/grafana

# Verify images are available
docker images mcp/grafana
```

#### "Command not found" (uvx/pipx)

```bash
# Install uvx
pip install uvx

# Test PagerDuty MCP server
uvx pagerduty-mcp --help
```

### Debug Commands

```bash
# Test individual servers
claude mcp get server-name

# Check Claude Code logs
claude --debug mcp list

# Test Docker connectivity
docker run --rm -i --network=host \
  -e GRAFANA_URL="http://localhost:3000" \
  -e GRAFANA_SERVICE_ACCOUNT_TOKEN="your-token" \
  mcp/grafana --help
```

### Configuration File Validation

Ensure your `.mcp.json` follows the correct format:

```json
{
  "mcpServers": {
    "server-name": {
      "command": "executable-command",
      "args": ["arg1", "arg2"],
      "env": {
        "ENV_VAR": "value"
      }
    }
  }
}
```

## Security Best Practices for Claude Code

1. **Use Project Scope**: Keep sensitive tokens in project `.mcp.json` (gitignored)
2. **Environment Variables**: Never commit tokens to version control
3. **Token Rotation**: Regularly rotate API tokens
4. **Minimal Permissions**: Use least-privilege access for service accounts

## Claude Code Advanced Configuration

### Custom Transport Types

```bash
# SSE (Server-Sent Events) transport
claude mcp add server-name --transport sse wss://example.com/mcp

# HTTP transport with custom headers
claude mcp add server-name --transport http https://api.example.com/mcp \
  --env CUSTOM_HEADER="Bearer token"
```

### Environment Variable Expansion

Use environment variables in `.mcp.json`:

```json
{
  "mcpServers": {
    "github-mcp": {
      "command": "claude",
      "args": ["mcp", "proxy"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}",
        "MCP_SERVER_URL": "${GITHUB_MCP_URL:-https://api.githubcopilot.com/mcp/}"
      }
    }
  }
}
```

Then set environment variables:

```bash
export GITHUB_TOKEN="your-token"
export GITHUB_MCP_URL="https://custom-github-mcp.com/"
```

## Next Steps

Once your MCP servers are configured:

1. **Explore capabilities**: Try different queries with GitHub Copilot Chat
2. **Create workflows**: Combine data from multiple servers in conversations
3. **Monitor usage**: Check server logs for performance insights
4. **Customize further**: Adjust server configurations based on your needs

For additional help:

- VSCode MCP Documentation: <https://code.visualstudio.com/docs/copilot/customization/mcp-servers>
- Grafana MCP Server: <https://github.com/grafana/mcp-grafana>
- GitHub MCP Server: <https://github.com/github/github-mcp-server>
- PagerDuty MCP Server: <https://github.com/PagerDuty/pagerduty-mcp-server>
