# Currency API Incident Response Runbook

## Overview

This runbook provides step-by-step procedures for responding to incidents in the Currency API service.
All procedures assume you have direct access to the production environment and can execute
Docker/system commands.

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

---

## 🔍 LOAD SOURCE ANALYSIS PROCEDURES

### Universal Load Analysis (Required for ALL load-related incidents)

> **Use these procedures for High Request Rate, CPU, Memory, or File Descriptor alerts**
>
> **Note**: Commands below use Docker logs, but you can perform equivalent queries using:
>
> - **Grafana/Loki**: Log queries and dashboards
> - **API calls**: Direct service endpoints for metrics
> - **MCP tools**: Grafana MCP server for automated queries
> - **Other monitoring tools**: Prometheus queries, Jaeger traces, etc.

#### Step 1: Multi-Dimensional Traffic Analysis

**Identify traffic patterns across IP, Account, and User dimensions using MCP Grafana tools:**

```python
# Analyze request sources by IP and account patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "POST"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=50,
    direction="backward"
)

# Search for specific suspicious IP patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "[SUSPICIOUS_IP]"',
    startRfc3339="[START_TIME]",
    endRfc3339="[END_TIME]",
    limit=30
)

# Analyze account ID patterns from structured logs
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "account_id"',
    startRfc3339="[START_TIME]",
    endRfc3339="[END_TIME]",
    limit=20
)

# Check current nginx connection metrics
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_active",
    queryType="instant",
    startTime="now"
)

# Check request rate patterns
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="rate(nginx_http_requests_total[5m])",
    queryType="instant",
    startTime="now"
)
```

#### Step 2: Behavioral Pattern Analysis

**Analyze authentication and request patterns using MCP tools:**

```python
# Check authentication failures by searching for error status codes
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "401" or |= "403"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=20
)

# Look for rapid-fire requests with account/user patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "account_id" |= "user_id"',
    startRfc3339="[5_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=25
)

# Check for rate limiting activity (429 responses)
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "429" or |= "rate" or |= "limit"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=15
)

# Analyze endpoint usage patterns and user agents
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "POST" or |= "GET"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=30
)
```

#### Step 3: Resource Correlation Analysis

**Correlate load patterns with system resources using MCP tools:**

```python
# Check current nginx connection metrics and system load
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_active",
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_writing",
    queryType="instant",
    startTime="now"
)

# Check request volume trends over time
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="rate(nginx_http_requests_total[5m])",
    queryType="instant",
    startTime="now"
)

# Analyze high response time patterns that might indicate resource stress
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "response_time_ms"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=20
)

# Check for data-heavy endpoint usage (convert/rates/history)
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "convert" or |= "rates" or |= "history"',
    startRfc3339="[10_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=25
)
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

```text
Load Source Analysis Results:
- Analysis Time: [timestamp]
- Top 3 IPs: [IPs and request counts]
- Top 3 Accounts: [Account IDs and request counts]
- Top 3 Users: [User IDs and request counts]
- Classification: [Legitimate/IP Abuse/Account Abuse/User Abuse/Endpoint Abuse/System Issue]
- Correlation with Resources: [CPU/Memory/Response time correlation]
- Recommended Action: [Based on classification above]
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

**When attack patterns detected, use MCP PagerDuty tools:**

```python
# Create security incident with complete evidence package
mcp__pagerduty__create_incident(
    create_model={
        "incident": {
            "title": "SECURITY ALERT: Automated Attack Against Currency API - IP [ATTACKER_IP]",
            "service": {"id": "P7C7J0L", "summary": "security"},
            "urgency": "high",
            "body": {
                "details": "SECURITY INCIDENT: [Complete attack analysis with IP, patterns, impact, and evidence]"
            }
        }
    }
)
```

### Security Evidence Collection (MCP-Based)

```python
# Collect comprehensive attack evidence using MCP tools
# 1. Identify suspicious IP patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "[SUSPICIOUS_IP]"',
    startRfc3339="[ATTACK_START]",
    endRfc3339="[ATTACK_END]",
    limit=30
)

# 2. Document account/user abuse patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "account_id" |= "[SUSPICIOUS_IP]"',
    startRfc3339="[ATTACK_START]",
    endRfc3339="[ATTACK_END]",
    limit=20
)

# 3. Analyze attack impact on system resources
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_active",
    queryType="range",
    startTime="[ATTACK_START]",
    endTime="[ATTACK_END]",
    stepSeconds=60
)
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

1. **Verify the alert is accurate using MCP tools:**

   ```python
   # Check if service is up via Prometheus metrics
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='up{job="currency-api"}',
       queryType="instant",
       startTime="now"
   )

   # Check recent API response success rate
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='rate(http_requests_total{job="currency-api",status_code="200"}[5m])',
       queryType="instant",
       startTime="now"
   )
   ```

2. **Check service status and recent errors:**

   ```python
   # Check recent application logs for errors
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "error" or |= "ERROR" or |= "exception"',
       startRfc3339="[5_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=20,
       direction="backward"
   )

   # Check service startup and health logs
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "currency-api" |= "startup" or |= "health"',
       startRfc3339="[10_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=15
   )
   ```

3. **Quick restart attempt:**

   ```bash
   # Restart the currency service (operational command)
   docker restart currency-api
   ```

   **Monitor restart progress using MCP:**

   ```python
   # Check if service comes back up
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='up{job="currency-api"}',
       queryType="instant",
       startTime="now"
   )

   # Monitor restart logs and errors
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "currency-api"',
       startRfc3339="[2_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=20,
       direction="backward"
   )
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

2. **Examine recent logs for errors using MCP:**

   ```python
   # Application errors from structured logs
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "currency-api" |= "error" or |= "ERROR" or |= "exception"',
       startRfc3339="[10_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=30
   )

   # Database connection and error patterns
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "postgres" or |= "database" |= "error" or |= "connection"',
       startRfc3339="[10_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=25
   )

   # Check for service startup failures
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "failed" or |= "timeout" or |= "crash"',
       startRfc3339="[15_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=20
   )
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

1. **Identify error patterns using MCP:**

   ```python
   # Check recent 5xx errors from structured logs
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "50" |= "status_code" or |= "500" or |= "502" or |= "503"',
       startRfc3339="[5_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=30
   )

   # Check error rate metrics from Prometheus
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m]))',
       queryType="instant",
       startTime="now"
   )

   # Check error rate percentage
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100',
       queryType="instant",
       startTime="now"
   )
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

3. **Examine resource constraints using MCP:**

   ```python
   # Check container resource usage via Prometheus
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='container_memory_usage_bytes{name="currency-api"}',
       queryType="instant",
       startTime="now"
   )

   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100',
       queryType="instant",
       startTime="now"
   )

   # Check nginx connection patterns for resource correlation
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='nginx_connections_active',
       queryType="instant",
       startTime="now"
   )

   # Monitor current request load
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='rate(http_requests_total{job="currency-api"}[5m])',
       queryType="instant",
       startTime="now"
   )
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

```python
# Check current request rate using MCP Prometheus
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='sum(rate(http_requests_total{job="currency-api"}[2m]))',
    queryType="instant",
    startTime="now"
)

# Monitor system impact from high request rate
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100',
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='container_memory_usage_bytes{name="currency-api"} / 1024 / 1024',
    queryType="instant",
    startTime="now"
)

# Check response times from production metrics
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000',
    queryType="instant",
    startTime="now"
)
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

**After completing load source analysis, perform these CPU-specific checks using MCP:**

```python
# Correlate CPU spike with request volume using metrics
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='rate(http_requests_total{job="currency-api"}[5m])',
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='rate(container_cpu_usage_seconds_total{name="currency-api"}[5m]) * 100',
    queryType="instant",
    startTime="now"
)

# Check for processing errors that might cause CPU loops
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "error" or |= "exception" or |= "timeout" or |= "retry"',
    startRfc3339="[5_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=30
)

# Check for database query issues causing high CPU
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "query" or |= "database" or |= "sql" or |= "postgres"',
    startRfc3339="[5_MINUTES_AGO]",
    endRfc3339="[NOW]",
    limit=25
)

# Check memory usage correlation with CPU spikes
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='container_memory_usage_bytes{name="currency-api"} / 1024 / 1024',
    queryType="instant",
    startTime="now"
)
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

1. **Correlate memory usage with request patterns:**

   ```bash
   # Check if memory spike correlates with request volume/type
   docker stats currency-api --no-stream
   docker logs currency-api --since=10m | wc -l

   # Look for requests that might generate large responses
   docker logs currency-api --since=10m | grep -E "(convert|rates|history)" | wc -l
   ```

2. **Analyze traffic sources during memory spike (IP, Account, User):**

   ```bash
   # Check for concentrated requests from specific IPs
   docker logs currency-api --since=10m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head -10

   # Check for specific accounts making memory-intensive requests
   docker logs currency-api --since=10m | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -10

   # Check for specific users making memory-intensive requests
   docker logs currency-api --since=10m | grep -oE '"user_id":"[^"]*"' | sort | uniq -c | sort -nr | head -10

   # Cross-reference top account with memory usage patterns
   TOP_ACCOUNT_MEM=$(docker logs currency-api --since=10m | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -1 | awk '{print $2}')
   echo "Top account during memory spike: $TOP_ACCOUNT_MEM"
   docker logs currency-api --since=10m | grep "$TOP_ACCOUNT_MEM" | wc -l

   # Look for large response patterns by account
   docker logs currency-api --since=10m | grep -E "200.*[0-9]{4,}" | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -5

   # Check for accounts requesting data-heavy endpoints
   docker logs currency-api --since=10m | grep -E "(history|rates)" | grep -oE '"account_id":"[^"]*"' | sort | uniq -c | sort -nr | head -5
   ```

3. **Check for memory leak vs. legitimate usage:**

   ```bash
   # Check for gradual memory increase (potential leak)
   echo "Monitoring memory trend..."
   for i in {1..3}; do
     docker stats currency-api --no-stream | awk 'NR==2 {print "Sample '$i':", $3, $4}'
     sleep 30
   done

   # Look for memory-related errors
   docker logs currency-api --since=10m | grep -i -E "memory|oom|alloc|leak"
   ```

#### Step 2: Memory-Specific Diagnostics

**After completing load source analysis, perform these memory-specific checks:**

```bash
# Check current memory usage and trends
docker stats currency-api --no-stream

# Monitor memory growth over time (potential leak detection)
echo "Monitoring memory for 90 seconds..."
for i in {1..3}; do
  docker stats currency-api --no-stream | awk 'NR==2 {print "Sample '$i':", $3, $4}'
  sleep 30
done

# Check for memory-related errors
docker logs currency-api --since=10m | grep -i -E "memory|oom|alloc|leak"

# Check database connection pool memory usage
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT count(*) as connections, state
FROM pg_stat_activity
GROUP BY state;"
```

#### Step 3: Resolution Actions

**Apply resolution based on load classification from Step 1:**

👉 **Use the decision tree from: [Step 4: Load Classification Decision Tree](#step-4-load-classification-decision-tree)**

**Memory-specific considerations:**

   ```bash
   # Check memory details inside container
   docker exec currency-api cat /proc/meminfo | grep -E "MemTotal|MemAvailable"
   ```

1. **Check application behavior:**

   ```bash
   # Check database connection pool memory usage
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT count(*) as connections, state
   FROM pg_stat_activity
   GROUP BY state;"
   ```

#### Memory Resolution Actions

**Based on memory load source analysis:**

1. **If memory spike due to legitimate high traffic/large responses:**
   - Document correlation between traffic patterns and memory usage
   - Monitor if memory usage stabilizes or continues growing
   - Consider response size optimization before scaling

2. **If memory spike due to specific account/IP requesting large data:**

   ```bash
   # Document account/IP patterns causing memory spikes
   # Consider response pagination or rate limiting for large requests
   # Escalate to account management if needed
   ```

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

   # Check Prometheus for latency trends
   # Navigate to: http://localhost:9090
   # Query: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[2m])) by (le))
   ```

2. **Identify slow endpoints:**

   ```bash
   # Check recent slow requests in logs
   docker logs currency-api --since=5m | grep -E "[0-9]{3,}\.[0-9]+ms" | tail -10

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

### Currency API Average Response Time High

**Alert:** Average response time >500ms for 1+ minute
**Severity:** Warning
**PagerDuty:** Warning notification

#### Average Latency Response Steps (Target: 2 minutes)

1. **Measure current performance:**

   ```bash
   # Test multiple endpoints
   for endpoint in health api/v1/rates api; do
     echo "Testing /$endpoint:"
     time curl -s http://localhost:8000/$endpoint > /dev/null
   done
   ```

2. **Check system load:**

   ```bash
   # Check overall system performance
   uptime
   docker stats --no-stream

   # Check I/O wait
   iostat -x 1 3
   ```

3. **Analyze request patterns:**

   ```bash
   # Check for expensive operations
   docker logs currency-api --since=3m | grep -E "(convert|rates)" | tail -10

   # Check concurrent request load
   docker logs currency-api --since=2m | grep -c "$(date +%H:%M)"
   ```

#### Average Latency Resolution Actions

1. **Performance tuning:**

   ```bash
   # Check database performance
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT schemaname, tablename, n_tup_ins, n_tup_upd, n_tup_del, n_tup_hot_upd
   FROM pg_stat_user_tables
   ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;"
   ```

**Escalation:** If average response time >1 second or trend continues rising.

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

**Alert:** `nginx_connections_active > 100` for 1+ minute
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

# Monitor connection patterns
docker logs nginx --since=5m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head-10

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

```python
# Check response time distribution using MCP Prometheus
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000',
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000',
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le)) * 1000',
    queryType="instant",
    startTime="now"
)

# Check endpoint-specific request rates and patterns
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='sum(rate(http_requests_total{job="currency-api"}[5m])) by (endpoint)',
    queryType="instant",
    startTime="now"
)

# Check error rates by endpoint and status code
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr='sum(rate(http_requests_total{job="currency-api"}[5m])) by (status_code)',
    queryType="instant",
    startTime="now"
)
```

### Troubleshooting Common Issues

#### "Service Unavailable" Errors

1. **Check service status using MCP:**

   ```python
   # Check if service is up via Prometheus
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='up{job="currency-api"}',
       queryType="instant",
       startTime="now"
   )

   # Check recent service logs for errors
   mcp__grafana__query_loki_logs(
       datasourceUid="loki",
       logql='{job="containerlogs"} |= "currency-api" |= "error" or |= "started" or |= "stopped"',
       startRfc3339="[10_MINUTES_AGO]",
       endRfc3339="[NOW]",
       limit=20
   )
   ```

2. **Verify service health and performance:**

   ```python
   # Check recent successful requests
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='rate(http_requests_total{job="currency-api",status_code="200"}[5m])',
       queryType="instant",
       startTime="now"
   )

   # Check current response times
   mcp__grafana__query_prometheus(
       datasourceUid="prometheus",
       expr='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le))',
       queryType="instant",
       startTime="now"
   )
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

### MCP Tools for Incident Response (PREFERRED)

#### Traffic Analysis and Load Source Investigation

```python
# Check current system metrics (nginx connections, request rates)
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_active",
    queryType="instant",
    startTime="now"
)

mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="rate(nginx_http_requests_total[5m])",
    queryType="instant",
    startTime="now"
)

# Search logs for suspicious IP patterns
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "[SUSPICIOUS_IP]"',
    startRfc3339="[INCIDENT_START]",
    endRfc3339="[NOW]",
    limit=30
)

# Analyze account/user patterns for attack detection
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "account_id"',
    startRfc3339="[INCIDENT_START]",
    endRfc3339="[NOW]",
    limit=25
)
```

#### Security Incident Management

```python
# Create security incident for attack patterns
mcp__pagerduty__create_incident(
    create_model={
        "incident": {
            "title": "SECURITY ALERT: [Attack Description]",
            "service": {"id": "P7C7J0L", "summary": "security"},
            "urgency": "high",
            "body": {"details": "[Complete attack evidence and analysis]"}
        }
    }
)

# Add incident updates with findings
mcp__pagerduty__add_note_to_incident(
    incident_id="[INCIDENT_ID]",
    note="[Analysis results and mitigation status]"
)

# Resolve incidents after mitigation
mcp__pagerduty__manage_incidents(
    manage_request={"incident_ids": ["[INCIDENT_ID]"], "status": "resolved"}
)
```

#### System Health Monitoring

```python
# Monitor nginx connection trends over time
mcp__grafana__query_prometheus(
    datasourceUid="prometheus",
    expr="nginx_connections_active",
    queryType="range",
    startTime="[30_MINUTES_AGO]",
    endTime="now",
    stepSeconds=60
)

# Check for rate limiting effectiveness
mcp__grafana__query_loki_logs(
    datasourceUid="loki",
    logql='{job="containerlogs"} |= "429" or |= "rate" or |= "limit"',
    startRfc3339="[POST_MITIGATION]",
    endRfc3339="[NOW]",
    limit=20
)
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

# Common metrics queries (execute in Prometheus UI at http://localhost:9090)
# Request rate: sum(rate(http_requests_total{job="currency-api"}[5m]))
# Error rate: sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="currency-api"}[5m])) * 100
# P95 latency: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="currency-api"}[5m])) by (le))
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

*Last Updated: $(date +%Y-%m-%d)*
*Runbook Version: 1.0*
