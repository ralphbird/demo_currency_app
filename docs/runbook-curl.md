# Currency API Incident Response Runbook (cURL Version)

## Overview

This runbook provides step-by-step procedures for responding to incidents in the Currency API service.
All procedures assume you have direct access to the production environment and can execute
Docker/system commands and cURL API calls to monitoring services.

**Service Architecture:**

- FastAPI application with PostgreSQL database
- Full observability stack: Prometheus, Grafana, Jaeger, Loki
- PagerDuty integration for critical/warning alerts
- Docker-based deployment with monitoring containers

**Key Service URLs:**

- Currency API: <http://localhost:8000>
- Grafana Dashboards: <http://localhost:3000> (admin/admin)
- Prometheus: <http://localhost:9090>
- Jaeger Tracing: <http://localhost:16686>

**API Authentication:**

For Grafana API calls, use the default credentials:

```bash
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"
```

## 🔧 PREREQUISITES CHECK

**Before using this runbook, ensure you have all required tools:**

```bash
# Run this prerequisite check before incident response
echo "=== Currency API Incident Response Prerequisites Check ==="

# Check for required command-line tools
MISSING_TOOLS=()

command -v curl >/dev/null 2>&1 || MISSING_TOOLS+=("curl")
command -v jq >/dev/null 2>&1 || MISSING_TOOLS+=("jq")
command -v docker >/dev/null 2>&1 || MISSING_TOOLS+=("docker")
command -v date >/dev/null 2>&1 || MISSING_TOOLS+=("date")
command -v bc >/dev/null 2>&1 || MISSING_TOOLS+=("bc")
command -v grep >/dev/null 2>&1 || MISSING_TOOLS+=("grep")
command -v awk >/dev/null 2>&1 || MISSING_TOOLS+=("awk")
command -v wc >/dev/null 2>&1 || MISSING_TOOLS+=("wc")

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
  echo "✅ All required tools are available"
else
  echo "❌ Missing required tools: ${MISSING_TOOLS[*]}"
  echo "Please install missing tools before proceeding"
  exit 1
fi

# Check Grafana API connectivity
echo "Testing Grafana API connectivity..."
if curl -f -s -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA_URL/api/health" >/dev/null 2>&1; then
  echo "✅ Grafana API is accessible"
else
  echo "❌ Cannot connect to Grafana API at $GRAFANA_URL"
  echo "Verify Grafana is running and credentials are correct"
fi

# Check Docker daemon connectivity
echo "Testing Docker daemon..."
if docker info >/dev/null 2>&1; then
  echo "✅ Docker daemon is accessible"
else
  echo "❌ Cannot connect to Docker daemon"
  echo "Verify Docker is running and you have appropriate permissions"
fi

echo "=== Prerequisites check complete ==="
```

**Installation Commands for Missing Tools:**

- **Ubuntu/Debian**: `sudo apt-get install curl jq docker.io bc grep coreutils`
- **RHEL/CentOS**: `sudo yum install curl jq docker bc grep coreutils`
- **macOS**: `brew install curl jq docker bc grep coreutils`

## 📅 DATE UTILITIES

**Standardized date formatting functions for consistent usage throughout the runbook:**

```bash
# Date utility functions - source these at the beginning of incident response
get_iso_timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}

get_timestamp_minutes_ago() {
  local minutes=${1:-10}
  date -d "$minutes minutes ago" -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
  date -v-"${minutes}M" -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
  echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"  # Fallback to now if date arithmetic fails
}

get_unix_timestamp_minutes_ago() {
  local minutes=${1:-10}
  date -d "$minutes minutes ago" '+%s' 2>/dev/null || \
  date -v-"${minutes}M" '+%s' 2>/dev/null || \
  date '+%s'  # Fallback to now if date arithmetic fails
}

get_backup_timestamp() {
  date '+%Y%m%d_%H%M%S'
}

get_human_timestamp() {
  date -u '+%Y-%m-%d %H:%M:%S UTC'
}

# Usage examples:
# NOW_ISO=$(get_iso_timestamp)
# TEN_MIN_AGO=$(get_timestamp_minutes_ago 10)
# ONE_HOUR_AGO=$(get_timestamp_minutes_ago 60)
# UNIX_NOW=$(date '+%s')
# UNIX_30MIN_AGO=$(get_unix_timestamp_minutes_ago 30)
```

## 🛠️ HELPER FUNCTIONS

**Common operation helpers to simplify incident response commands:**

```bash
# Grafana API helper functions
query_prometheus_metric() {
  local metric="$1"
  local fallback="${2:-unknown}"
  curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
    --data-urlencode "query=$metric" \
    | jq -r ".data.result[0].value[1] // \"$fallback\"" 2>/dev/null || echo "query_failed"
}

query_loki_logs() {
  local logql="$1"
  local minutes_ago="${2:-10}"
  local limit="${3:-20}"
  local start_time=$(get_timestamp_minutes_ago "$minutes_ago")

  curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
    --data-urlencode "query=$logql" \
    --data-urlencode "start=$start_time" \
    --data-urlencode "limit=$limit" \
    --data-urlencode "direction=backward" \
    | jq -r '.data.result[]?.values[]?[1] // empty' 2>/dev/null
}

# System health check helpers
check_service_health() {
  local service_name="$1"
  echo "=== $service_name Health Check ==="

  if docker ps --format "{{.Names}}" | grep -q "^${service_name}$"; then
    echo "✅ Container '$service_name' is running"

    # Check container resource usage
    docker stats "$service_name" --no-stream --format \
      "CPU: {{.CPUPerc}} | Memory: {{.MemUsage}} ({{.MemPerc}})"
  else
    echo "❌ Container '$service_name' is not running"
    return 1
  fi
}

check_grafana_connectivity() {
  if curl -f -s -u "$GRAFANA_USER:$GRAFANA_PASS" "$GRAFANA_URL/api/health" >/dev/null 2>&1; then
    echo "✅ Grafana API is accessible"
    return 0
  else
    echo "❌ Cannot connect to Grafana API at $GRAFANA_URL"
    return 1
  fi
}

# Log analysis helpers
get_top_ips() {
  local minutes="${1:-10}"
  local count="${2:-10}"
  docker logs currency-api --since="${minutes}m" 2>/dev/null | \
    grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | \
    sort | uniq -c | sort -nr | head -"$count"
}

get_top_accounts() {
  local minutes="${1:-10}"
  local count="${2:-10}"
  docker logs currency-api --since="${minutes}m" 2>/dev/null | \
    grep -oE '"account_id":"[^"]*"' | \
    sort | uniq -c | sort -nr | head -"$count"
}

check_error_rate() {
  local threshold="${1:-5}"
  local error_rate=$(query_prometheus_metric \
    'sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100' \
    '0')

  if [ "$error_rate" != "query_failed" ] && [ "$error_rate" != "0" ]; then
    if [ "$(echo "$error_rate > $threshold" | bc 2>/dev/null)" = "1" ]; then
      echo "❌ High error rate: ${error_rate}% (threshold: ${threshold}%)"
      return 1
    else
      echo "✅ Error rate normal: ${error_rate}%"
    fi
  else
    echo "⚠️  Cannot determine error rate"
    return 2
  fi
}

# Usage examples:
# SERVICE_UP=$(query_prometheus_metric 'up{job="currency-api"}' '0')
# RECENT_ERRORS=$(query_loki_logs '{job="containerlogs"} |= "error"' 5 30)
# check_service_health currency-api
# TOP_IPS=$(get_top_ips 30 5)
# check_error_rate 10
```

---

## 🔍 LOAD SOURCE ANALYSIS PROCEDURES

### Universal Load Analysis (Required for ALL load-related incidents)

> **Use these procedures for High Request Rate, CPU, Memory, or File Descriptor alerts**
>
> **Note**: Commands below use Docker logs, but you can perform equivalent queries using:
>
> - **Grafana/Loki**: Log queries via cURL API calls
> - **Prometheus**: Metrics queries via cURL API calls
> - **Direct API calls**: Direct service endpoints for metrics
> - **Other monitoring tools**: Prometheus queries, Jaeger traces, etc.

#### Step 1: Multi-Dimensional Traffic Analysis

**Identify traffic patterns across IP, Account, and User dimensions using Grafana API calls:**

```bash
# Set up authentication for Grafana API
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Source the date utilities functions first
source <(cat << 'EOF'
get_iso_timestamp() {
  date -u '+%Y-%m-%dT%H:%M:%SZ'
}
get_timestamp_minutes_ago() {
  local minutes=${1:-10}
  date -d "$minutes minutes ago" -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
  date -v-"${minutes}M" -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null || \
  echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
}
EOF
)

# Analyze request sources by IP and account patterns (Loki logs)
START_TIME=$(get_timestamp_minutes_ago 10)
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "POST"' \
  --data-urlencode "start=$START_TIME" \
  --data-urlencode "limit=50" \
  --data-urlencode "direction=backward"

# Search for specific suspicious IP patterns
# IMPORTANT: Replace the IP below with the actual suspicious IP address
SUSPICIOUS_IP="192.168.1.100"  # CHANGE THIS to the actual suspicious IP
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode "query={job=\"containerlogs\"} |= \"$SUSPICIOUS_IP\"" \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=30"

# Analyze account ID patterns from structured logs
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "account_id"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=20"

# Check current nginx connection metrics (Prometheus)
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=nginx_connections_active'

# Check request rate patterns
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(nginx_http_requests_total[5m])'
```

#### Step 2: Behavioral Pattern Analysis

**Analyze authentication and request patterns using Grafana API:**

```bash
# Check authentication failures by searching for error status codes
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "401" or |= "403"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=20"

# Look for rapid-fire requests with account/user patterns
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "account_id" |= "user_id"' \
  --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
  --data-urlencode "limit=25"

# Check for rate limiting activity (429 responses)
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "429" or |= "rate" or |= "limit"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=15"

# Analyze endpoint usage patterns and user agents
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "POST" or |= "GET"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=30"
```

#### Step 3: Resource Correlation Analysis

**Correlate load patterns with system resources using Grafana API:**

```bash
# Check current nginx connection metrics and system load
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=nginx_connections_active'

curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=nginx_connections_writing'

# Check request volume trends over time
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(nginx_http_requests_total[5m])'

# Analyze high response time patterns that might indicate resource stress
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "response_time_ms"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=20"

# Check for data-heavy endpoint usage (convert/rates/history)
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "convert" or |= "rates" or |= "history"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=25"
```

#### Step 4: Load Classification Decision Tree

**Based on analysis results, classify the load source:**

1. **Legitimate Traffic Spike** (Distributed IPs/accounts/users, normal patterns)
   - Multiple IPs, accounts, users contributing
   - Authentication success rates normal
   - Request patterns match business usage
   - **Action:** Monitor closely, consider scaling with business context

2. **IP-Based Abuse** (Concentrated traffic from few IPs)
   - Few IPs generating majority of traffic
   - May include failed authentication attempts
   - **Action:** Consider IP-based rate limiting, document for blocking

3. **Account-Based Abuse** (Single account excessive load)
   - One or few accounts generating disproportionate load
   - May involve multiple users within account
   - **Action:** Account management escalation, account-level throttling

4. **User-Based Abuse** (Single user excessive load)
   - Specific user generating excessive requests
   - Check if associated with suspicious account patterns
   - **Action:** User-level throttling, account management review

5. **Endpoint Abuse** (Specific endpoint being hammered)
   - Unusual concentration on specific API endpoints
   - Check if endpoint has performance issues
   - **Action:** Endpoint-specific rate limiting, performance review

6. **System Issue** (Load without clear external cause)
   - No obvious traffic source correlation
   - May indicate internal loops, memory leaks, or bugs
   - **Action:** System restart, code investigation

### Load Analysis Documentation Template

**Always document findings in incident notes using this format:**

```bash
# Generate documentation with actual analysis results (using standardized date utilities)
ANALYSIS_TIME=$(get_human_timestamp)

# Extract top IPs from your log analysis (example command)
TOP_IPS=$(docker logs currency-api --since=10m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head -3)

# Extract top accounts from your log analysis
TOP_ACCOUNTS=$(docker logs currency-api --since=10m | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -3)

# Create load analysis documentation
cat << EOF
Load Source Analysis Results:
- Analysis Time: $ANALYSIS_TIME
- Top 3 IPs: $TOP_IPS
- Top 3 Accounts: $TOP_ACCOUNTS
- Top 3 Users: [Extract from logs using similar pattern to accounts]
- Classification: [Choose: Legitimate/IP Abuse/Account Abuse/User Abuse/Endpoint Abuse/System Issue]
- Correlation with Resources: [Document CPU/Memory/Response time patterns observed]
- Recommended Action: [Based on classification - rate limiting, blocking, scaling, investigation]
EOF
```

---

## 🛡️ SECURITY ESCALATION PROCEDURES

### Attack Pattern Recognition (CRITICAL ADDITION)

**Immediate Security Escalation Required When:**

1. **External IP Indicators:**
   - Single external IP >50% of total traffic
   - IP with no legitimate business relationship
   - Non-browser user agents (Python, curl, automated tools)

2. **Behavioral Red Flags:**
   - Multiple synthetic account/user combinations from same IP
   - Sustained high-frequency requests (>100 req/min per IP)
   - Targeting business-critical endpoints exclusively
   - Automated tool signatures in user agents (aiohttp, requests, etc.)

3. **Resource Impact:**
   - >200% threshold overrun with concentrated source
   - Sustained load >10 minutes from single source
   - Evidence of evasion tactics (account cycling, IP rotation)

### Security Incident Creation Process

**When attack patterns detected, use PagerDuty API:**

```bash
# Set up PagerDuty API credentials
PAGERDUTY_API_KEY="your_api_key_here"  # Replace with actual key
PAGERDUTY_EMAIL="your_email@company.com"  # Replace with your email

# Validate PagerDuty prerequisites
if [ -z "$PAGERDUTY_API_KEY" ] || [ "$PAGERDUTY_API_KEY" = "your_api_key_here" ]; then
  echo "❌ PAGERDUTY_API_KEY not configured. Set your actual API key before proceeding."
  exit 1
fi

if [ -z "$PAGERDUTY_EMAIL" ] || [ "$PAGERDUTY_EMAIL" = "your_email@company.com" ]; then
  echo "❌ PAGERDUTY_EMAIL not configured. Set your actual email before proceeding."
  exit 1
fi

# Test PagerDuty API connectivity
echo "Testing PagerDuty API connectivity..."
if curl -f -s -H "Authorization: Token token=$PAGERDUTY_API_KEY" \
  -H "Content-Type: application/json" \
  https://api.pagerduty.com/users/me >/dev/null 2>&1; then
  echo "✅ PagerDuty API is accessible"
else
  echo "❌ Cannot connect to PagerDuty API. Check your API key and network connectivity."
  exit 1
fi

# Create security incident with complete evidence package
ATTACKER_IP="192.168.1.100"  # Replace with actual attacking IP address
SERVICE_ID="P7C7J0L"  # Replace with your actual PagerDuty service ID

# Construct incident details with evidence
INCIDENT_DETAILS="SECURITY INCIDENT: Automated attack detected from IP $ATTACKER_IP. Analysis shows: [ADD SPECIFIC EVIDENCE FROM YOUR ANALYSIS - request patterns, account abuse, resource impact, etc.]"

curl -X POST \
  -H "Authorization: Token token=$PAGERDUTY_API_KEY" \
  -H "Content-Type: application/json" \
  -H "From: $PAGERDUTY_EMAIL" \
  -d "{
    \"incident\": {
      \"type\": \"incident\",
      \"title\": \"SECURITY ALERT: Automated Attack Against Currency API - IP $ATTACKER_IP\",
      \"service\": {
        \"id\": \"$SERVICE_ID\",
        \"type\": \"service_reference\"
      },
      \"urgency\": \"high\",
      \"body\": {
        \"type\": \"incident_body\",
        \"details\": \"$INCIDENT_DETAILS\"
      }
    }
  }" \
  https://api.pagerduty.com/incidents
```

### Security Evidence Collection (cURL-Based)

```bash
# Collect comprehensive attack evidence using Grafana API
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# 1. Identify suspicious IP patterns
SUSPICIOUS_IP="192.168.1.100"  # Replace with actual suspicious IP
echo "Collecting IP evidence for $SUSPICIOUS_IP..."
if curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query_range" \
  --data-urlencode "query={job=\"containerlogs\"} |= \"$SUSPICIOUS_IP\"" \
  --data-urlencode "start=$(date -d '1 hour ago' --iso-8601)" \
  --data-urlencode "end=$(date --iso-8601)" \
  --data-urlencode "limit=100" \
  | jq -r '.data.result[]?.values[]?[1] // empty' > attack_evidence_ip.log 2>/dev/null; then
  echo "IP evidence collected: $(wc -l < attack_evidence_ip.log) log entries"
else
  echo "ERROR: Failed to collect IP evidence" | tee attack_evidence_ip.log
fi

# 2. Document account/user abuse patterns
echo "Collecting account pattern evidence..."
if curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query_range" \
  --data-urlencode "query={job=\"containerlogs\"} |= \"account_id\" |= \"$SUSPICIOUS_IP\"" \
  --data-urlencode "start=$(date -d '1 hour ago' --iso-8601)" \
  --data-urlencode "end=$(date --iso-8601)" \
  --data-urlencode "limit=50" \
  | jq -r '.data.result[]?.values[]?[1] // empty' > attack_evidence_accounts.log 2>/dev/null; then
  echo "Account evidence collected: $(wc -l < attack_evidence_accounts.log) log entries"
else
  echo "ERROR: Failed to collect account evidence" | tee attack_evidence_accounts.log
fi

# 3. Analyze attack impact on system resources
echo "Collecting resource impact data..."
if curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query_range" \
  --data-urlencode 'query=nginx_connections_active' \
  --data-urlencode "start=$(date -d '1 hour ago' +%s)" \
  --data-urlencode "end=$(date +%s)" \
  --data-urlencode "step=60" \
  | jq -r '.data.result[]?.values[] // empty' > attack_impact_connections.json 2>/dev/null; then
  echo "Resource impact data collected: $(wc -l < attack_impact_connections.json) data points"
else
  echo "ERROR: Failed to collect resource impact data" | tee attack_impact_connections.json
fi

# Create evidence package
echo "Attack Evidence Package - $(date)" > security_incident_evidence.txt
echo "==================================" >> security_incident_evidence.txt
echo "" >> security_incident_evidence.txt
echo "Suspicious IP: $SUSPICIOUS_IP" >> security_incident_evidence.txt
echo "Attack Duration: $(date -d '1 hour ago') to $(date)" >> security_incident_evidence.txt
echo "" >> security_incident_evidence.txt
echo "Log Analysis Results:" >> security_incident_evidence.txt
echo "- IP-based logs: $(wc -l < attack_evidence_ip.log) entries" >> security_incident_evidence.txt
echo "- Account patterns: $(wc -l < attack_evidence_accounts.log) entries" >> security_incident_evidence.txt
```

### Parallel Actions Required

**During security escalation:**

1. **Continue infrastructure mitigation** (rate limiting, blocking)
2. **Document all attack characteristics** for investigation
3. **Preserve logs and evidence** for forensic analysis
4. **Coordinate with security team** on blocking recommendations

---

## 🚨 CRITICAL ALERTS

### Currency API Service Down

**Alert:** `up{job="currency-api"} != 1` for 30+ seconds
**Severity:** Critical
**PagerDuty:** Immediately escalated

#### Immediate Response (Target: 2 minutes)

1. **Verify the alert is accurate using Grafana API:**

   ```bash
   # Set up authentication for Grafana API
   GRAFANA_USER="admin"
   GRAFANA_PASS="admin"
   GRAFANA_URL="http://localhost:3000"

   # Check if service is up via Prometheus metrics
   SERVICE_STATUS=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=up{job="currency-api"}' \
     | jq -r '.data.result[0].value[1] // "unknown"' 2>/dev/null || echo "query_failed")
   echo "Service up status: $SERVICE_STATUS"

   # Check recent API response success rate
   SUCCESS_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=rate(http_requests_total{job="currency-api",status_code="200"}[5m])' \
     | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "query_failed")
   echo "Success rate: $SUCCESS_RATE requests/sec"
   ```

2. **Check service status and recent errors:**

   ```bash
   # Check recent application logs for errors
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "error" or |= "ERROR" or |= "exception"' \
     --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
     --data-urlencode "limit=20" \
     --data-urlencode "direction=backward" \
     | jq -r '.data.result[]?.values[]?[1] // empty' | head -10

   # Check service startup and health logs
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "currency-api" |= "startup" or |= "health"' \
     --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
     --data-urlencode "limit=15" \
     | jq -r '.data.result[]?.values[]?[1] // empty' | head -10
   ```

3. **Quick restart attempt:**

   ```bash
   # Restart the currency service (operational command)
   docker restart currency-api
   ```

   **Monitor restart progress using Grafana API:**

   ```bash
   # Check if service comes back up (wait 30 seconds, then check)
   sleep 30
   RESTART_STATUS=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=up{job="currency-api"}' \
     | jq -r '.data.result[0].value[1] // "unknown"' 2>/dev/null || echo "query_failed")
   echo "Service status after restart: $RESTART_STATUS"

   # Monitor restart logs and errors
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "currency-api"' \
     --data-urlencode "start=$(date -d '2 minutes ago' --iso-8601)" \
     --data-urlencode "limit=20" \
     --data-urlencode "direction=backward" \
     | jq -r '.data.result[]?.values[]?[1] // empty' | head -10
   ```

#### Deep Investigation (if restart fails)

1. **Check system resources:**

   ```bash
   # Check available disk space
   df -h

   # Check memory usage
   free -h

   # Check if Docker daemon is running
   docker info
   ```

2. **Examine recent logs for errors using Grafana API:**

   ```bash
   # Application errors from structured logs
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "currency-api" |= "error" or |= "ERROR" or |= "exception"' \
     --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
     --data-urlencode "limit=30" \
     | jq -r '.data.result[]?.values[]?[1] // empty' > service_errors.log

   # Database connection and error patterns
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "postgres" or |= "database" |= "error" or |= "connection"' \
     --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
     --data-urlencode "limit=25" \
     | jq -r '.data.result[]?.values[]?[1] // empty' > database_errors.log

   # Check for service startup failures
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "failed" or |= "timeout" or |= "crash"' \
     --data-urlencode "start=$(date -d '15 minutes ago' --iso-8601)" \
     --data-urlencode "limit=20" \
     | jq -r '.data.result[]?.values[]?[1] // empty' > startup_failures.log

   # Display error summaries
   echo "=== Service Errors ==="
   cat service_errors.log
   echo "=== Database Errors ==="
   cat database_errors.log
   echo "=== Startup Failures ==="
   cat startup_failures.log
   ```

3. **Full stack restart (if needed):**

   ```bash
   # Stop all services
   make down

   # Start all services
   make up

   # Monitor startup
   make logs
   ```

**Escalation:** If service doesn't recover within 10 minutes, escalate to senior engineer.

### Currency API High Error Rate

**Alert:** 5xx error rate >5% for 2+ minutes
**Severity:** Critical
**PagerDuty:** Immediately escalated

#### Error Rate Immediate Response (Target: 3 minutes)

1. **Identify error patterns using Grafana API:**

   ```bash
   GRAFANA_USER="admin"
   GRAFANA_PASS="admin"
   GRAFANA_URL="http://localhost:3000"

   # Check recent 5xx errors from structured logs
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "50" |= "status_code" or |= "500" or |= "502" or |= "503"' \
     --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
     --data-urlencode "limit=30" \
     | jq -r '.data.result[]?.values[]?[1] // empty' | head -15

   # Check error rate metrics from Prometheus
   ERROR_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m]))' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Current 5xx error rate: $ERROR_RATE errors/sec"

   # Check error rate percentage
   ERROR_PERCENTAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Current error percentage: $ERROR_PERCENTAGE%"
   ```

2. **Check database connectivity:**

   ```bash
   # Test database connection
   docker exec -it postgres psql -U currency_user -d currency_db -c "SELECT 1;"

   # Check for database locks
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT pid, state, query, query_start
   FROM pg_stat_activity
   WHERE state != 'idle'
   ORDER BY query_start;"
   ```

3. **Examine resource constraints using Grafana API:**

   ```bash
   # Check container resource usage via Prometheus
   MEMORY_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=container_memory_usage_bytes{name="currency-api"}' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Memory usage: $(echo "scale=2; $MEMORY_USAGE / 1024 / 1024" | bc) MB"

   CPU_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "CPU usage: $CPU_USAGE%"

   # Check nginx connection patterns for resource correlation
   NGINX_CONNECTIONS=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=nginx_connections_active' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Active nginx connections: $NGINX_CONNECTIONS"

   # Monitor current request load
   REQUEST_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=rate(http_requests_total{job="currency-api"}[5m])' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Current request rate: $REQUEST_RATE requests/sec"
   ```

#### Resolution Steps

1. **If database connection issues:**

   ```bash
   # Restart database
   docker restart postgres

   # Wait for database startup
   sleep 10

   # Restart API service
   docker restart currency-api
   ```

2. **If resource exhaustion:**

   ```bash
   # Check container limits
   docker inspect currency-api | grep -A 10 "Resources"

   # Consider scaling (if using orchestration)
   # Or restart to clear memory leaks
   docker restart currency-api
   ```

**Escalation:** If error rate doesn't drop below 2% within 15 minutes, escalate immediately.

---

## ⚠️ WARNING ALERTS

### Currency API High Request Rate

**Alert:** Request rate >20 RPS for 2+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Step 1: Request Rate Load Source Analysis (REQUIRED)

**🔍 Perform complete load source analysis before any other action:**

👉 **Go to: [Load Source Analysis Procedures](#-load-source-analysis-procedures)**

Complete all 4 steps of the Universal Load Analysis to identify traffic sources and
classify the load pattern.

#### Step 2: Request Rate Specific Checks

**After completing load source analysis, perform these request-rate specific checks:**

```bash
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Check current request rate using Grafana Prometheus API
REQUEST_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api"}[2m]))' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "Current request rate: $REQUEST_RATE requests/sec"

# Monitor system impact from high request rate
CPU_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "CPU usage: $CPU_USAGE%"

MEMORY_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=container_memory_usage_bytes{name="currency-api"} / 1024 / 1024' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "Memory usage: $MEMORY_USAGE MB"

# Check response times from production metrics
P95_LATENCY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "P95 response time: $P95_LATENCY ms"
```

#### Step 3: Request Rate Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**Request-rate specific considerations:**

- If high rate is impacting performance, prioritize rate limiting over scaling
- Check if rate increase correlates with business events or marketing campaigns
- Consider temporary rate limits while investigating source
- Document rate patterns in incident timeline for trend analysis

**Escalation:** If traffic continues >50 RPS for 10+ minutes or causes performance degradation.

### Currency API High CPU Usage

**Alert:** CPU >80% for 3+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Step 1: CPU Load Source Analysis (REQUIRED)

**🔍 Perform complete load source analysis before any other action:**

👉 **Go to: [Load Source Analysis Procedures](#-load-source-analysis-procedures)**

Complete all 4 steps of the Universal Load Analysis to identify traffic sources and
classify the load pattern.

#### Step 2: CPU-Specific Diagnostics

**After completing load source analysis, perform these CPU-specific checks using Grafana API:**

```bash
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Correlate CPU spike with request volume using metrics
REQUEST_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(http_requests_total{job="currency-api"}[5m])' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "Current request rate: $REQUEST_RATE requests/sec"

CPU_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "Current CPU usage: $CPU_USAGE%"

# Check for processing errors that might cause CPU loops
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "error" or |= "exception" or |= "timeout" or |= "retry"' \
  --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
  --data-urlencode "limit=30" \
  | jq -r '.data.result[]?.values[]?[1] // empty' | head -10

# Check for database query issues causing high CPU
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "query" or |= "database" or |= "sql" or |= "postgres"' \
  --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
  --data-urlencode "limit=25" \
  | jq -r '.data.result[]?.values[]?[1] // empty' | head -10

# Check memory usage correlation with CPU spikes
MEMORY_USAGE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=container_memory_usage_bytes{name="currency-api"} / 1024 / 1024' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "Memory usage: $MEMORY_USAGE MB"
```

#### Step 3: CPU Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**CPU-specific considerations:**

- If CPU spikes are correlated with specific requests, investigate those endpoints
- Consider database query optimization before scaling CPU resources
- Check for infinite loops or processing errors in application logs
- Monitor for memory leaks that might cause increased garbage collection CPU usage

**Escalation:** If CPU >90% for 10+ minutes or causes request timeouts.

### Currency API High Memory Usage

**Alert:** Memory >1GB for 5+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Step 1: Memory Load Source Analysis (REQUIRED)

**🔍 Perform complete load source analysis before any other action:**

👉 **Go to: [Load Source Analysis Procedures](#-load-source-analysis-procedures)**

Complete all 4 steps of the Universal Load Analysis to identify traffic sources and
classify the load pattern.

#### Step 2: Memory-Specific Diagnostics

**After completing load source analysis, perform these memory-specific checks:**

```bash
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Check current memory usage and trends
docker stats currency-api --no-stream

# Monitor memory growth over time (potential leak detection)
echo "Monitoring memory for 90 seconds..."
for i in {1..3}; do
  MEMORY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
    "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
    --data-urlencode 'query=container_memory_usage_bytes{name="currency-api"} / 1024 / 1024' \
    | jq -r '.data.result[0].value[1] // "0"')
  echo "Sample $i: ${MEMORY} MB"
  sleep 30
done

# Check for memory-related errors in logs
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "memory" or |= "oom" or |= "alloc" or |= "leak"' \
  --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
  --data-urlencode "limit=20" \
  | jq -r '.data.result[]?.values[]?[1] // empty'

# Check database connection pool memory usage
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT count(*) as connections, state
FROM pg_stat_activity
GROUP BY state;"
```

#### Step 3: Memory Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**Memory-specific considerations:**

1. **If memory spike due to legitimate high traffic/large responses:**
   - Document correlation between traffic patterns and memory usage
   - Monitor if memory usage stabilizes or continues growing
   - Consider response size optimization before scaling

2. **If memory spike due to specific account/IP requesting large data:**
   - Document account/IP patterns causing memory spikes
   - Consider response pagination or rate limiting for large requests
   - Escalate to account management if needed

3. **If gradual memory increase detected (potential memory leak):**

   ```bash
   # Restart container to clear potential memory leak
   docker restart currency-api

   # Monitor memory after restart
   docker stats currency-api --no-stream

   # Document memory growth pattern for development team
   ```

4. **If memory spike due to database connection issues:**

   ```bash
   # Check database connection pool
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT count(*) as connections, state
   FROM pg_stat_activity
   GROUP BY state;"

   # Consider connection pool tuning before scaling
   ```

**IMPORTANT:** Understand memory consumption pattern before considering scaling memory limits.

**Escalation:** If memory >1.5GB or shows continuous growth pattern.

### Currency API High File Descriptor Usage

**Alert:** FD usage >80% for 2+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Step 1: File Descriptor Load Source Analysis (REQUIRED)

**🔍 Perform complete load source analysis before any other action:**

👉 **Go to: [Load Source Analysis Procedures](#-load-source-analysis-procedures)**

Complete all 4 steps of the Universal Load Analysis to identify traffic sources and
classify the load pattern.

#### Step 2: File Descriptor Specific Diagnostics

**After completing load source analysis, perform these FD-specific checks:**

```bash
# Check current FD usage and limit
docker exec currency-api ls /proc/self/fd | wc -l
docker exec currency-api ulimit -n

# Identify what's consuming file descriptors
docker exec currency-api lsof -p 1 | head -20

# Check for socket connections
docker exec currency-api ss -tuln | wc -l

# Check database connections
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE state = 'active';"

# Check network connections
docker exec currency-api netstat -an | grep ESTABLISHED | wc -l
```

#### Step 3: File Descriptor Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**FD-specific considerations:**

- High FD usage often indicates connection leaks or excessive concurrent connections
- Check if increase correlates with high request rate from load source analysis
- Database connection pooling issues are common causes
- Consider connection limits before restarting services

**Escalation:** If FD usage >90% or restart doesn't resolve the issue.

### Currency API High Response Time (P95)

**Alert:** 95th percentile >1 second for 1+ minute
**Severity:** Warning
**PagerDuty:** Warning notification

#### P95 Response Steps (Target: 2 minutes)

1. **Check current performance:**

   ```bash
   # Test response time manually
   time curl -s http://localhost:8000/health
   time curl -s http://localhost:8000/api/v1/rates

   # Check Grafana for latency trends using API
   GRAFANA_USER="admin"
   GRAFANA_PASS="admin"
   GRAFANA_URL="http://localhost:3000"

   P95_LATENCY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[2m])) by (le))' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Current P95 latency: $(echo "$P95_LATENCY * 1000" | bc) ms"
   ```

2. **Identify slow endpoints:**

   ```bash
   # Check recent slow requests in logs using Grafana
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |~ "[0-9]{3,}\\.[0-9]+ms"' \
     --data-urlencode "start=$(date -d '5 minutes ago' --iso-8601)" \
     --data-urlencode "limit=10" \
     | jq -r '.data.result[]?.values[]?[1] // empty'

   # Check database query performance
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   WHERE mean_time > 100
   ORDER BY mean_time DESC
   LIMIT 5;"
   ```

3. **Check system resources:**

   ```bash
   # Check if resource constraints causing slowness
   docker stats --no-stream | grep -E "(currency-api|postgres)"
   ```

#### P95 Resolution Actions

1. **Database optimization:**

   ```bash
   # Check for blocking queries
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT pid, state, wait_event, query
   FROM pg_stat_activity
   WHERE state != 'idle' AND wait_event IS NOT NULL;"
   ```

2. **If performance doesn't improve:**

   ```bash
   # Consider service restart
   docker restart currency-api
   ```

**Escalation:** If P95 latency >2 seconds or affecting user experience.

### Nginx Load Balancer Down

**Alert:** `nginx_up != 1` for 1+ minute
**Severity:** Critical
**PagerDuty:** Immediately escalated

#### Nginx Immediate Response (Target: 2 minutes)

1. **Verify nginx container status:**

   ```bash
   # Check if nginx container is running
   docker ps | grep nginx

   # Check nginx health
   curl -f http://localhost/ || echo "Nginx unreachable"
   ```

2. **Check nginx logs:**

   ```bash
   # View nginx logs
   docker logs nginx --tail=50 -f

   # Check for configuration errors
   docker logs nginx --since=10m | grep -i error
   ```

3. **Quick restart attempt:**

   ```bash
   # Restart nginx service
   docker restart nginx

   # Monitor restart progress
   docker logs nginx --tail=20 -f
   ```

#### Nginx Deep Investigation (if restart fails)

1. **Check nginx configuration:**

   ```bash
   # Test nginx configuration
   docker exec nginx nginx -t

   # Check configuration files
   docker exec nginx cat /etc/nginx/nginx.conf
   ```

2. **Check upstream services:**

   ```bash
   # Verify backend services are accessible
   curl -f http://localhost:8000/health

   # Check if nginx can reach backends
   docker exec nginx curl -f http://currency-api:8000/health
   ```

**Escalation:** If nginx doesn't recover within 5 minutes, escalate immediately.

### Nginx High Connections

**Alert:** `nginx_connections_active > 200` for 1+ minute
**Severity:** Warning
**PagerDuty:** Warning notification

#### Step 1: Connection Load Source Analysis (REQUIRED)

**🔍 Perform complete load source analysis before any other action:**

👉 **Go to: [Load Source Analysis Procedures](#-load-source-analysis-procedures)**

Complete all 4 steps of the Universal Load Analysis to identify traffic sources and
classify the load pattern.

#### Step 2: Connection Analysis

**After completing load source analysis, perform nginx-specific checks:**

```bash
# Check current connection status
curl -s http://localhost/nginx_status | grep -E "(Active|Reading|Writing|Waiting)"

# Monitor connection patterns using Docker logs
docker logs nginx --since=5m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head -10

# Check for connection timeouts or errors
docker logs nginx --since=10m | grep -i -E "(timeout|error|limit)"
```

#### Step 3: Nginx Connection Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**Connection-specific considerations:**

- High connections often indicate traffic spikes or slow backend responses
- Check if connections are legitimate traffic or potential DDoS
- Consider connection limits and rate limiting before scaling
- Monitor backend response times that may cause connection buildup

**Escalation:** If connections >200 or backend services show stress.

### Nginx Request Rate Drop

**Alert:** `rate(nginx_http_requests_total[5m]) < 0.1` for 1+ minute
**Severity:** Warning
**PagerDuty:** Warning notification

#### Request Rate Drop Analysis (Target: 3 minutes)

1. **Verify the drop is real:**

   ```bash
   # Check current nginx request rate
   curl -s http://localhost/nginx_status

   # Compare with backend API rate
   curl -s http://localhost:8000/metrics | grep http_requests_total

   # Check if nginx is processing requests
   docker logs nginx --since=5m | tail -20
   ```

2. **Check for nginx issues:**

   ```bash
   # Check nginx error logs
   docker logs nginx --since=10m | grep -i error

   # Verify nginx is accepting connections
   curl -I http://localhost/

   # Check upstream connectivity
   docker exec nginx curl -f http://currency-api:8000/health
   ```

3. **Analyze potential causes:**

   ```bash
   # Check if backend services are healthy
   curl -f http://localhost:8000/health

   # Look for rate limiting or blocking
   docker logs nginx --since=10m | grep -E "(limit|block|deny)"

   # Check system resources
   docker stats nginx --no-stream
   ```

#### Request Rate Drop Resolution

1. **If nginx configuration issue:**

   ```bash
   # Test nginx configuration
   docker exec nginx nginx -t

   # Reload nginx if configuration is valid
   docker exec nginx nginx -s reload
   ```

2. **If upstream connectivity issue:**

   ```bash
   # Check backend services
   docker ps | grep currency-api

   # Restart backend if needed (with approval)
   # docker restart currency-api
   ```

**Escalation:** If request rate doesn't recover within 10 minutes or affects user traffic.

---

## 🔧 MAINTENANCE PROCEDURES

> **Quick Commands**: For common maintenance commands, see [Common Commands Reference](#-common-commands-reference)

### Service Operations

#### Deployment and Rollback

**Deploy New Version:**

```bash
# Pull latest changes
git pull origin main

# Rebuild and deploy
make rebuild

# Verify deployment
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/rates | jq .

# Check for errors
docker logs currency-api --tail=20
```

**Rollback Procedure:**

```bash
# Check current commit
git log --oneline -5

# Rollback to specific commit
git checkout <last_good_commit>

# Rebuild with previous version
make rebuild

# Verify rollback
curl -f http://localhost:8000/health
docker logs currency-api --tail=10
```

#### Service Management

**Container Operations:**

```bash
# Graceful service restart
docker restart currency-api

# Force restart if unresponsive
docker kill currency-api && docker start currency-api

# Full stack operations
make down    # Stop all services
make up      # Start all services
make rebuild # Rebuild and restart
```

### Data Management

#### Database Operations

> **Database Commands**: See [Common Commands Reference](#-common-commands-reference)
> for detailed database diagnostic commands.

**Backup and Restore:**

```bash
# Create timestamped backup
docker exec postgres pg_dump -U currency_user -d currency_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Emergency restore (stops API service)
docker stop currency-api
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i postgres psql -U currency_user -d currency_db
docker start currency-api
```

**Performance Maintenance:**

```bash
# Regular maintenance (run weekly)
docker exec postgres psql -U currency_user -d currency_db -c "VACUUM ANALYZE;"

# Check database health
docker exec postgres psql -U currency_user -d currency_db -c "SELECT version();"
```

#### Exchange Rate Data

**Data Updates:**

```bash
# Regenerate fresh rate data
poetry run python scripts/generate_demo_data.py

# Validate USD base currency (should always be 1.0)
docker exec postgres psql -U currency_user -d currency_db -c "SELECT * FROM exchange_rates WHERE currency_code = 'USD';"

# Check all 10 supported currencies exist
docker exec postgres psql -U currency_user -d currency_db -c "SELECT COUNT(DISTINCT currency_code) FROM exchange_rates;"
```

#### Authentication Management

**JWT Operations:**

> **JWT Commands**: See [Common Commands Reference](#-common-commands-reference) for JWT token generation.

**Secret Rotation:**

```bash
# Generate new JWT secret and restart services
openssl rand -hex 32    # Update JWT_SECRET_KEY in environment
make down && make up    # Restart to pick up new secret
```

### System Maintenance

#### Log Management

**Log Collection (for incidents):**

```bash
# Collect timestamped logs from all services
mkdir -p logs/$(date +%Y%m%d_%H%M%S)
docker logs currency-api > logs/$(date +%Y%m%d_%H%M%S)/currency-api.log 2>&1
docker logs postgres > logs/$(date +%Y%m%d_%H%M%S)/postgres.log 2>&1
```

> **Log Analysis**: See [Common Commands Reference](#-common-commands-reference)
> for detailed log analysis commands.

#### System Cleanup

**Regular Maintenance (run monthly):**

```bash
# Clean up Docker resources
docker image prune -f    # Remove unused images
docker volume prune -f   # Remove unused volumes
docker network prune -f  # Remove unused networks

# Check disk usage
df -h    # Ensure adequate free space for logs and database
```

---

## 📊 MONITORING & DIAGNOSTICS

### Service URLs & Access

#### Production Monitoring Stack

- **Grafana Dashboards**: <http://localhost:3000>
  - Username: `admin`
  - Password: `admin`
  - Currency API Dashboard: Pre-configured with metrics
  - Logs Dashboard: Centralized log viewing

- **Prometheus Metrics**: <http://localhost:9090>
  - Query interface for custom metrics
  - Alert rule configuration
  - Target health monitoring

- **Jaeger Tracing**: <http://localhost:16686>
  - Distributed request tracing
  - Performance analysis
  - Error correlation

- **Currency API**: <http://localhost:8000>
  - Health endpoint: `/health`
  - Metrics endpoint: `/metrics`
  - API docs: `/docs`
  - OpenAPI spec: `/openapi.json`

#### Key Grafana Dashboard Queries

**Request Rate:**

```promql
sum(rate(http_requests_total{job="currency-api"}[5m]))
```

**Error Rate:**

```promql
sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100
```

**Response Time (P95):**

```promql
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le))
```

**Memory Usage:**

```promql
process_resident_memory_bytes{job="currency-api"} / (1024 * 1024 * 1024)
```

**CPU Usage:**

```promql
rate(process_cpu_seconds_total{job="currency-api"}[5m]) * 100
```

### Quick Health Checks

#### Service Status Verification

```bash
# Check all services are running
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Verify API responsiveness
curl -f http://localhost:8000/health | jq .

# Check database connectivity
curl -f http://localhost:8000/api/v1/rates | jq '.rates | length'

# Verify monitoring stack
curl -f http://localhost:9090/-/healthy
curl -f http://localhost:3000/api/health
```

#### Performance Baseline Checks

```bash
# Test conversion endpoint performance
time curl -X POST http://localhost:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $(poetry run python -c 'from currency_app.auth.jwt_auth import generate_jwt_token; print(generate_jwt_token("test", "test"))')" \
  -d '{"from_currency": "USD", "to_currency": "EUR", "amount": 100}'

# Check metrics endpoint response time
time curl -s http://localhost:8000/metrics | wc -l

# Verify database query performance
time docker exec -it postgres psql -U currency_user -d currency_db -c "SELECT COUNT(*) FROM conversions;"
```

### Diagnostic Commands

#### System Resource Analysis

```bash
# Check disk space (critical for logs/database)
df -h

# Check memory usage across all containers
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check network connectivity between containers
docker network ls
docker network inspect demo_currency_app_default | jq '.[0].Containers'
```

#### Database Diagnostics

```bash
# Check active database connections
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT
    pid,
    usename,
    application_name,
    client_addr,
    state,
    query_start,
    LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start DESC;"

# Check database locks
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT
    t.relname,
    l.locktype,
    page,
    virtualtransaction,
    pid,
    mode,
    granted
FROM pg_locks l, pg_stat_all_tables t
WHERE l.relation = t.relid
ORDER BY relation ASC;"

# Check slow queries (if pg_stat_statements enabled)
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT
    query,
    calls,
    total_time,
    mean_time,
    rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"
```

#### Application Performance Analysis

```bash
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Check response time distribution using Grafana API
P50_LATENCY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "P50 response time: $P50_LATENCY ms"

P90_LATENCY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "P90 response time: $P90_LATENCY ms"

P99_LATENCY=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "P99 response time: $P99_LATENCY ms"

# Check endpoint-specific request rates and patterns
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api"}[5m])) by (endpoint)' \
  | jq '.data.result[] | "\(.metric.endpoint // "unknown"): \(.value[1])"'

# Check error rates by endpoint and status code
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api"}[5m])) by (status_code)' \
  | jq '.data.result[] | "Status \(.metric.status_code // "unknown"): \(.value[1]) req/s"'
```

### Troubleshooting Common Issues

#### "Service Unavailable" Errors

1. **Check service status using Grafana API:**

   ```bash
   GRAFANA_USER="admin"
   GRAFANA_PASS="admin"
   GRAFANA_URL="http://localhost:3000"

   # Check if service is up via Prometheus
   SERVICE_UP=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=up{job="currency-api"}' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Service up status: $SERVICE_UP"

   # Check recent service logs for errors
   curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
     --data-urlencode 'query={job="containerlogs"} |= "currency-api" |= "error" or |= "started" or |= "stopped"' \
     --data-urlencode "start=$(date -d '10 minutes ago' --iso-8601)" \
     --data-urlencode "limit=20" \
     | jq -r '.data.result[]?.values[]?[1] // empty' | head -10
   ```

2. **Verify service health and performance:**

   ```bash
   # Check recent successful requests
   SUCCESS_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=rate(http_requests_total{job="currency-api",status_code="200"}[5m])' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "Success rate: $SUCCESS_RATE req/s"

   # Check current response times
   P95_RESPONSE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
     "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
     --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le))' \
     | jq -r '.data.result[0].value[1] // "0"')
   echo "P95 response time: $(echo "$P95_RESPONSE * 1000" | bc) ms"
   ```

#### Database Connection Issues

1. **Verify PostgreSQL is running:**

   ```bash
   docker logs postgres --tail=10
   docker exec postgres pg_isready -U currency_user -d currency_db
   ```

2. **Check connection limits:**

   ```bash
   docker exec -it postgres psql -U currency_user -d currency_db -c "SHOW max_connections;"
   docker exec -it postgres psql -U currency_user -d currency_db -c "SELECT COUNT(*) FROM pg_stat_activity;"
   ```

3. **Test connection from API container:**

   ```bash
   docker exec currency-api nc -zv postgres 5432
   ```

#### Authentication Problems

1. **Verify JWT configuration:**

   ```bash
   docker exec currency-api env | grep JWT
   ```

2. **Test token generation:**

   ```bash
   poetry run python -c "
   from currency_app.auth.jwt_auth import generate_jwt_token
   print('Token generated successfully:', generate_jwt_token('test', 'test')[:50] + '...')
   "
   ```

3. **Check token validation:**

   ```bash
   TOKEN=$(poetry run python -c "from currency_app.auth.jwt_auth import generate_jwt_token; print(generate_jwt_token('test', 'test'))")
   curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/rates -v
   ```

### Escalation Contacts

#### Severity Levels

##### Critical (Page immediately)

- Service completely down
- Error rate >10%
- Data corruption suspected

##### Warning (Business hours)

- Performance degradation
- Resource usage warnings
- Non-critical functionality issues

#### Contact Information

- **Primary On-Call**: PagerDuty integration
- **Engineering Team**: Escalate via PagerDuty after 15 minutes
- **Database Administrator**: For database-specific issues
- **Infrastructure Team**: For Docker/container issues

#### Information to Include in Escalation

1. **Alert details**: Which alert triggered, when, duration
2. **Impact assessment**: Affected functionality, user impact
3. **Steps taken**: What diagnostic steps have been performed
4. **Current status**: Service state, error rates, resource usage
5. **Logs**: Relevant error messages or suspicious patterns

---

## 📚 COMMON COMMANDS REFERENCE

### Grafana API Tools for Incident Response (PREFERRED)

#### Traffic Analysis and Load Source Investigation

```bash
# Set up authentication for all Grafana API calls
GRAFANA_USER="admin"
GRAFANA_PASS="admin"
GRAFANA_URL="http://localhost:3000"

# Check current system metrics (nginx connections, request rates)
NGINX_CONNECTIONS=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=nginx_connections_active' \
  | jq -r '.data.result[0].value[1] // "unknown"' 2>/dev/null || echo "query_failed")
echo "Nginx active connections: $NGINX_CONNECTIONS"

REQUEST_RATE=$(curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query" \
  --data-urlencode 'query=rate(nginx_http_requests_total[5m])' \
  | jq -r '.data.result[0].value[1] // "0"' 2>/dev/null || echo "query_failed")
echo "Request rate: $REQUEST_RATE requests/sec"

# Search logs for suspicious IP patterns
SUSPICIOUS_IP="192.168.1.100"  # Replace with actual IP
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode "query={job=\"containerlogs\"} |= \"$SUSPICIOUS_IP\"" \
  --data-urlencode "start=$(date -d '30 minutes ago' --iso-8601)" \
  --data-urlencode "limit=30" \
  | jq -r '.data.result[]?.values[]?[1] // empty'

# Analyze account/user patterns for attack detection
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "account_id"' \
  --data-urlencode "start=$(date -d '30 minutes ago' --iso-8601)" \
  --data-urlencode "limit=25" \
  | jq -r '.data.result[]?.values[]?[1] // empty'
```

#### Security Incident Management

```bash
# Set up PagerDuty API credentials
PAGERDUTY_API_KEY="your_api_key_here"  # Replace with actual key
PAGERDUTY_EMAIL="your_email@company.com"  # Replace with your email

# Create security incident for attack patterns
ATTACK_DESCRIPTION="[DESCRIBE THE SPECIFIC ATTACK TYPE: e.g., 'High-frequency API requests from single IP', 'Account enumeration attack', 'DDoS attempt']"
ATTACK_EVIDENCE="[PROVIDE SPECIFIC EVIDENCE: e.g., 'IP 1.2.3.4 generated 500+ requests in 5 minutes targeting /api/v1/convert endpoint with multiple account IDs']"

curl -X POST \
  -H "Authorization: Token token=$PAGERDUTY_API_KEY" \
  -H "Content-Type: application/json" \
  -H "From: $PAGERDUTY_EMAIL" \
  -d "{
    \"incident\": {
      \"type\": \"incident\",
      \"title\": \"SECURITY ALERT: $ATTACK_DESCRIPTION\",
      \"service\": {
        \"id\": \"P7C7J0L\",
        \"type\": \"service_reference\"
      },
      \"urgency\": \"high\",
      \"body\": {
        \"type\": \"incident_body\",
        \"details\": \"$ATTACK_EVIDENCE\"
      }
    }
  }" \
  https://api.pagerduty.com/incidents

# Add incident updates with findings
INCIDENT_ID="your_incident_id"  # Replace with actual incident ID from previous command response
ANALYSIS_UPDATE="[UPDATE WITH CURRENT STATUS: e.g., 'Rate limiting applied to attacking IP. Request volume decreased by 80%. Monitoring for evasion tactics.']"

curl -X POST \
  -H "Authorization: Token token=$PAGERDUTY_API_KEY" \
  -H "Content-Type: application/json" \
  -H "From: $PAGERDUTY_EMAIL" \
  -d "{
    \"note\": {
      \"content\": \"$ANALYSIS_UPDATE\"
    }
  }" \
  "https://api.pagerduty.com/incidents/$INCIDENT_ID/notes"

# Resolve incidents after mitigation
curl -X PUT \
  -H "Authorization: Token token=$PAGERDUTY_API_KEY" \
  -H "Content-Type: application/json" \
  -H "From: $PAGERDUTY_EMAIL" \
  -d '{
    "incident": {
      "type": "incident",
      "status": "resolved"
    }
  }' \
  "https://api.pagerduty.com/incidents/$INCIDENT_ID"
```

#### System Health Monitoring

```bash
# Monitor nginx connection trends over time
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/2/api/v1/query_range" \
  --data-urlencode 'query=nginx_connections_active' \
  --data-urlencode "start=$(date -d '30 minutes ago' +%s)" \
  --data-urlencode "end=$(date +%s)" \
  --data-urlencode "step=60" \
  | jq '.data.result[] | .values[]'

# Check for rate limiting effectiveness
curl -G -s -u "$GRAFANA_USER:$GRAFANA_PASS" \
  "$GRAFANA_URL/api/datasources/proxy/1/loki/api/v1/query" \
  --data-urlencode 'query={job="containerlogs"} |= "429" or |= "rate" or |= "limit"' \
  --data-urlencode "start=$(date -d '15 minutes ago' --iso-8601)" \
  --data-urlencode "limit=20" \
  | jq -r '.data.result[]?.values[]?[1] // empty'
```

### Database Diagnostic Commands

#### Connection Analysis

```bash
# Check active database connections
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT pid, usename, application_name, client_addr, state, query_start,
       LEFT(query, 50) as query_preview
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY query_start DESC;"

# Check total connection count by state
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT count(*) as connections, state
FROM pg_stat_activity
GROUP BY state;"

# Check for connection limit issues
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT setting as max_connections,
       (SELECT count(*) FROM pg_stat_activity) as current_connections
FROM pg_settings WHERE name = 'max_connections';"
```

#### Performance Analysis

```bash
# Check slow queries (if pg_stat_statements enabled)
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT query, calls, total_time, mean_time, rows
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;"

# Check for blocking queries
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT pid, state, wait_event, query
FROM pg_stat_activity
WHERE state != 'idle' AND wait_event IS NOT NULL;"

# Check database locks
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT t.relname, l.locktype, page, virtualtransaction, pid, mode, granted
FROM pg_locks l, pg_stat_all_tables t
WHERE l.relation = t.relid
ORDER BY relation ASC;"
```

### Container Management Commands

#### Status and Health Checks

```bash
# Check all service containers status
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check specific service health
curl -f http://localhost:8000/health | jq .

# Check resource usage across all containers
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"

# Check specific container resources
docker stats currency-api --no-stream
```

#### Container Service Operations

```bash
# Restart specific service
docker restart currency-api

# View service logs (recent)
docker logs currency-api --tail=50 -f

# View service logs (time-based)
docker logs currency-api --since=10m

# Full stack restart
make down && make up
```

### Log Analysis Commands

#### Error Pattern Detection

```bash
# Find recent errors
docker logs currency-api --since=10m | grep -i error

# Search for specific error patterns
docker logs currency-api --since=30m | grep -E "(500|timeout|connection|database)"

# Check authentication failures
docker logs currency-api --since=1h | grep -E "(401|403|unauthorized|forbidden)"
```

#### Traffic Analysis

```bash
# Count requests by IP
docker logs currency-api --since=10m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head -10

# Count requests by account
docker logs currency-api --since=10m | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -10

# Count requests by user
docker logs currency-api --since=10m | grep -oE '"user_id":"[^"]*"' | sort | uniq -c | sort -nr | head -10

# Analyze endpoint usage
docker logs currency-api --since=10m | grep -oE "(GET|POST) [^ ]+" | sort | uniq -c | sort -nr
```

### System Resource Commands

#### System Health

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check system load
uptime

# Check network connectivity between containers
docker network inspect demo_currency_app_default | jq '.[0].Containers'
```

#### Process Analysis

```bash
# Check container process info
docker exec currency-api ps aux

# Check file descriptor usage
docker exec currency-api ls /proc/self/fd | wc -l
docker exec currency-api ulimit -n

# Check network connections
docker exec currency-api netstat -an | grep ESTABLISHED | wc -l
```

### Monitoring Stack Commands

#### Prometheus Queries

```bash
# Check if Prometheus is healthy
curl -f http://localhost:9090/-/healthy

# Common metrics queries (execute directly via API)
PROMETHEUS_URL="http://localhost:9090"

# Request rate
curl -G "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api"}[5m]))'

# Error rate
curl -G "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100'

# P95 latency
curl -G "$PROMETHEUS_URL/api/v1/query" \
  --data-urlencode 'query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le))'
```

#### Grafana Access

```bash
# Check Grafana health
curl -f http://localhost:3000/api/health

# Access Grafana dashboards at http://localhost:3000 (admin/admin)
```

### Authentication Commands

#### JWT Token Management

```bash
# Generate test JWT token
poetry run python -c "
from currency_app.auth.jwt_auth import generate_jwt_token
token = generate_jwt_token('test-account', 'test-user')
print(f'JWT Token: {token}')
"

# Test API with JWT token
TOKEN=$(poetry run python -c "from currency_app.auth.jwt_auth import generate_jwt_token; print(generate_jwt_token('test', 'test'))")
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/rates
```

---

## 📋 QUICK REFERENCE

### Emergency Commands

```bash
# Full service restart
make down && make up

# Service health check
curl -f http://localhost:8000/health

# Database connectivity test
docker exec postgres pg_isready -U currency_user -d currency_db

# Check all container status
docker ps --format "table {{.Names}}\t{{.Status}}"

# View recent errors
docker logs currency-api --since=10m | grep -i error

# Generate emergency JWT token
poetry run python -c "from currency_app.auth.jwt_auth import generate_jwt_token; print(generate_jwt_token('emergency', 'responder'))"
```

### Key Metrics Thresholds

| Metric | Warning | Critical | Notes |
|--------|---------|----------|-------|
| CPU Usage | >80% (3min) | >95% (1min) | Per container |
| Memory Usage | >1GB (5min) | >2GB (2min) | Per container |
| Error Rate | >2% (2min) | >5% (2min) | 5xx responses |
| Response Time P95 | >1s (1min) | >3s (30s) | All endpoints |
| Request Rate | >20 RPS (2min) | >50 RPS (5min) | Sustained |
| File Descriptors | >80% (2min) | >95% (1min) | Of limit |

### Service Recovery Checklist

- [ ] Verify all containers running (`docker ps`)
- [ ] Check service health (`curl http://localhost:8000/health`)
- [ ] Test database connectivity
- [ ] Verify monitoring stack accessible
- [ ] Check recent logs for errors
- [ ] Test API functionality with valid JWT
- [ ] Confirm metrics are being collected
- [ ] Validate alert channels working

---

*Last Updated: 2025-01-03*
*Runbook Version: 2.0 (cURL Edition)*
