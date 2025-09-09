# MCP Servers Setup Guide for VSCode GitHub Copilot

This guide sets up three MCP (Model Context Protocol) servers to extend GitHub Copilot with
Grafana, GitHub, and PagerDuty integrations.

## 🚀 Quick Start (5 Minutes)

1. **Enable MCP**: VSCode Settings → Search "copilot mcp" → Check "Enable MCP"
2. **Install tools**: `pip install uv` and `docker pull mcp/grafana`
3. **Start services**: `make up` (starts your local Grafana)
4. **Get tokens**: Create service account token in Grafana + PagerDuty User API token
5. **Restart VSCode**: Enter tokens when prompted

**That's it!** Skip to [Testing Your Setup](#testing-your-setup) to verify everything works.

---

## 📋 Detailed Setup Checklist

- [ ] VSCode 1.101+ with GitHub Copilot extension
- [ ] Enable MCP in VSCode settings
- [ ] Install required tools (uv, Docker)
- [ ] Configure authentication for each service
- [ ] Test server connections

## Prerequisites

### Required Software

1. **VSCode 1.101 or later** with GitHub Copilot extension installed
2. **Python 3.8+** with `uv` installed globally:

   ```bash
   pip install uv
   ```

3. **Optional**: Docker (for local GitHub MCP server)

### Enable MCP in VSCode

1. Open VSCode Settings (`Cmd/Ctrl + ,`)
2. Search for "copilot mcp"
3. Check "GitHub Copilot › Chat: Enable MCP"

## Server Configuration

The configuration is already set up in `.vscode/mcp.json`. Here's what each server provides:

### 1. GitHub MCP Server

- **Status**: ✅ Ready to use (remote hosted)
- **Capabilities**: Repository management, GitHub Actions, code security, issues/PRs
- **Authentication**: Uses your existing GitHub Copilot authentication

### 2. Grafana MCP Server

- **Status**: ⏳ Requires Docker services running + authentication setup
- **Capabilities**: Dashboard management, metrics queries, alert rules
- **URL**: Pre-configured for local Docker instance (<http://localhost:3000>)
- **Authentication**: Service Account Token required

### 3. PagerDuty MCP Server

- **Status**: ⏳ Requires authentication setup
- **Capabilities**: Incident management, on-call schedules, escalation policies
- **Authentication**: User API Token required

## Authentication Setup

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

#### Step 1: Verify uv Installation

```bash
# Check if uv is installed
uv --version

# If not installed:
pip install uv
```

#### Step 2: Create PagerDuty API Token

1. Log into your PagerDuty account
2. Go to **User Settings** (click your profile picture → **My Profile**)
3. Select **User API Tokens** tab
4. Click **Create API Token**
5. Enter description: `VSCode MCP Integration`
6. **Copy and save the token securely**

#### Step 3: Test PagerDuty Connection

```bash
# Test the pagerduty-mcp-server package
uvx pagerduty-mcp-server --help

# Test connection (replace with your token)
PAGERDUTY_API_KEY="your-token" uvx pagerduty-mcp-server --enable-write-tools
```

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

## Testing Your Setup

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
2. Verify the binary is installed and in PATH:

   ```bash
   which mcp-grafana
   which uvx
   ```

3. Test commands manually in terminal

#### "Authentication failed"

1. **Grafana**: Verify service account token has correct permissions
2. **PagerDuty**: Verify API token is a User API Token (not Integration Key)
3. Re-enter credentials in VSCode input prompts

#### "Docker image not found"

```bash
# Pull the Grafana MCP Docker image
docker pull mcp/grafana

# Verify the image is available
docker images mcp/grafana
```

#### "uvx command not found"

```bash
# Install uv if missing
pip install uv

# Ensure PATH includes uv binaries
export PATH="$HOME/.local/bin:$PATH"
```

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

   # Test PagerDuty MCP
   PAGERDUTY_API_KEY="your-token" uvx pagerduty-mcp-server --help
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

### GitHub MCP Server

- Repository information and statistics
- Issue and pull request management
- GitHub Actions workflow data
- Code security scanning results
- Branch and commit information

### Grafana MCP Server

- Dashboard listing and queries
- Panel data retrieval
- Alert rule management
- Data source queries
- Annotation management

### PagerDuty MCP Server

- Incident creation and management
- On-call schedule queries
- Service and escalation policy information
- Integration management
- Analytics and reporting data

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
