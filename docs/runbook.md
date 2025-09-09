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

## 🚨 CRITICAL ALERTS

### Currency API Service Down

**Alert:** `up{job="currency-api"} != 1` for 30+ seconds
**Severity:** Critical
**PagerDuty:** Immediately escalated

#### Immediate Response (Target: 2 minutes)

1. **Verify the alert is accurate:**

   ```bash
   # Check if containers are running
   docker ps | grep currency

   # Check service health endpoint
   curl -f http://localhost:8000/health || echo "Service unreachable"
   ```

2. **Check container status:**

   ```bash
   # View all service containers
   make logs

   # Check specific currency API logs
   docker logs currency-api --tail=50 -f
   ```

3. **Quick restart attempt:**

   ```bash
   # Restart the currency service
   docker restart currency-api

   # Monitor restart progress
   docker logs currency-api --tail=20 -f
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

2. **Examine recent logs for errors:**

   ```bash
   # Application errors
   docker logs currency-api --since=10m | grep -i error

   # Database connection issues
   docker logs postgres --since=10m | grep -i error
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

#### Immediate Response (Target: 3 minutes)

1. **Identify error patterns:**

   ```bash
   # Check recent application logs for 5xx errors
   docker logs currency-api --since=5m | grep -E "50[0-9]"

   # Check error patterns in Prometheus
   # Navigate to: http://localhost:9090
   # Query: sum(rate(http_requests_total{job="currency-api",status_code=~"5.."}[5m]))
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

3. **Examine resource constraints:**

   ```bash
   # Check if API container is resource-constrained
   docker stats currency-api --no-stream

   # Check file descriptor usage
   docker exec currency-api ls -la /proc/self/fd | wc -l
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

#### Response Steps (Target: 5 minutes)

1. **Analyze traffic patterns:**

   ```bash
   # Check current request rate in Prometheus
   # Navigate to: http://localhost:9090
   # Query: sum(rate(http_requests_total{job="currency-api"}[2m]))

   # Check request sources in logs
   docker logs currency-api --since=5m | grep -E "GET|POST" | tail -20
   ```

2. **Identify potential causes:**

   ```bash
   # Check for repeated requests from same IP
   docker logs currency-api --since=10m | grep -oE "[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" | sort | uniq -c | sort -nr | head -10

   # Check endpoint distribution
   docker logs currency-api --since=5m | grep -oE "(GET|POST) [^ ]+" | sort | uniq -c | sort -nr
   ```

3. **Monitor system impact:**

   ```bash
   # Check if high traffic is causing performance issues
   docker stats currency-api --no-stream

   # Check response times
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
   ```

#### Resolution Actions

1. **If legitimate traffic spike:**
   - Monitor system resources closely
   - Consider scaling if using orchestration
   - Alert business stakeholders if needed

2. **If potential abuse:**

   ```bash
   # Check authentication patterns
   docker logs currency-api --since=10m | grep -i "401\|403" | tail -10

   # Consider rate limiting (review nginx/reverse proxy config)
   ```

**Escalation:** If traffic continues >50 RPS for 10+ minutes or causes performance degradation.

### Currency API High CPU Usage

**Alert:** CPU >80% for 3+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Response Steps (Target: 3 minutes)

1. **Confirm CPU utilization:**

   ```bash
   # Check container CPU usage
   docker stats currency-api --no-stream

   # Check host CPU usage
   top -p $(docker inspect --format='{{.State.Pid}}' currency-api)
   ```

2. **Identify CPU-intensive processes:**

   ```bash
   # Check if it's related to request volume
   docker logs currency-api --since=5m | wc -l

   # Look for processing errors or loops
   docker logs currency-api --since=5m | grep -i -E "error|exception|timeout"
   ```

3. **Check for resource contention:**

   ```bash
   # Check all container resource usage
   docker stats --no-stream

   # Check system load
   uptime
   ```

#### CPU Resolution Actions

1. **Immediate mitigation:**

   ```bash
   # If sustained high CPU with no errors, consider restart
   docker restart currency-api

   # Monitor CPU after restart
   docker stats currency-api --no-stream
   ```

2. **If CPU remains high:**

   ```bash
   # Check database query performance
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY total_time DESC
   LIMIT 10;"
   ```

**Escalation:** If CPU >90% for 10+ minutes or causes request timeouts.

### Currency API High Memory Usage

**Alert:** Memory >1GB for 5+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Memory Response Steps (Target: 3 minutes)

1. **Analyze memory usage patterns:**

   ```bash
   # Check current memory usage
   docker stats currency-api --no-stream

   # Check memory details inside container
   docker exec currency-api cat /proc/meminfo | grep -E "MemTotal|MemAvailable"
   ```

2. **Look for memory leaks:**

   ```bash
   # Check for gradual memory increase
   # Monitor for 2-3 minutes
   for i in {1..6}; do
     docker stats currency-api --no-stream | awk 'NR==2 {print $3, $4}'
     sleep 30
   done
   ```

3. **Check application behavior:**

   ```bash
   # Look for memory-related errors
   docker logs currency-api --since=10m | grep -i -E "memory|oom|alloc"

   # Check for large response payloads
   docker logs currency-api --since=5m | grep -E "200.*[0-9]{4,}" | tail -5
   ```

#### Memory Resolution Actions

1. **Immediate mitigation:**

   ```bash
   # If memory appears to be leaking, restart container
   docker restart currency-api

   # Monitor memory after restart
   docker stats currency-api --no-stream
   ```

2. **If memory usage remains high:**

   ```bash
   # Check database connection pool
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT count(*) as connections, state
   FROM pg_stat_activity
   GROUP BY state;"
   ```

**Escalation:** If memory >1.5GB or shows continuous growth pattern.

### Currency API High File Descriptor Usage

**Alert:** FD usage >80% for 2+ minutes
**Severity:** Warning
**PagerDuty:** Warning notification

#### Response Steps (Target: 2 minutes)

1. **Check file descriptor usage:**

   ```bash
   # Check current FD usage
   docker exec currency-api ls /proc/self/fd | wc -l

   # Check FD limit
   docker exec currency-api ulimit -n
   ```

2. **Identify FD usage patterns:**

   ```bash
   # Check what's consuming file descriptors
   docker exec currency-api lsof -p 1 | head -20

   # Check for socket connections
   docker exec currency-api ss -tuln | wc -l
   ```

3. **Look for connection leaks:**

   ```bash
   # Check database connections
   docker exec -it postgres psql -U currency_user -d currency_db -c "
   SELECT count(*) as active_connections
   FROM pg_stat_activity
   WHERE state = 'active';"

   # Check network connections
   docker exec currency-api netstat -an | grep ESTABLISHED | wc -l
   ```

#### FD Resolution Actions

1. **Immediate mitigation:**

   ```bash
   # Restart to clear leaked connections
   docker restart currency-api

   # Verify FD usage after restart
   sleep 10
   docker exec currency-api ls /proc/self/fd | wc -l
   ```

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

---

## 🔧 MAINTENANCE PROCEDURES

### JWT Token Management

#### Generate New JWT Tokens

For testing or integration purposes:

```bash
# Generate a test token (expires in 1 hour)
poetry run python -c "
from currency_app.auth.jwt_auth import generate_jwt_token
token = generate_jwt_token('test-account', 'test-user')
print(f'JWT Token: {token}')
"

# Generate a long-lived token (24 hours)
poetry run python -c "
from currency_app.auth.jwt_auth import generate_jwt_token
from datetime import timedelta
token = generate_jwt_token('prod-account', 'service-user', expires_delta=timedelta(hours=24))
print(f'Long-lived JWT Token: {token}')
"
```

#### Rotate JWT Secret Key

1. **Generate new secret:**

   ```bash
   # Generate new JWT secret
   openssl rand -hex 32
   ```

2. **Update environment:**

   ```bash
   # Update docker-compose.yml or .env file
   # Set new JWT_SECRET_KEY value

   # Restart services to pick up new secret
   make down
   make up
   ```

3. **Verify new tokens:**

   ```bash
   # Test with new token
   NEW_TOKEN=$(poetry run python -c "from currency_app.auth.jwt_auth import generate_jwt_token; print(generate_jwt_token('test', 'test'))")
   curl -H "Authorization: Bearer $NEW_TOKEN" http://localhost:8000/api/v1/rates
   ```

### Database Maintenance

#### PostgreSQL Health Checks

```bash
# Check database connectivity
docker exec -it postgres psql -U currency_user -d currency_db -c "SELECT version();"

# Check database size
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT pg_size_pretty(pg_database_size('currency_db')) as db_size;"

# Check table sizes
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;"
```

#### Database Backup Procedures

```bash
# Create database backup
docker exec postgres pg_dump -U currency_user -d currency_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_$(date +%Y%m%d_%H%M%S).sql

# Verify backup file
ls -la backup_*.sql.gz
```

#### Database Restore (Emergency)

```bash
# Stop API service first
docker stop currency-api

# Restore from backup
gunzip -c backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i postgres psql -U currency_user -d currency_db

# Restart API service
docker start currency-api

# Verify restore
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT COUNT(*) FROM exchange_rates;
SELECT COUNT(*) FROM historical_rates;
SELECT COUNT(*) FROM conversions;"
```

#### Database Performance Maintenance

```bash
# Update table statistics
docker exec -it postgres psql -U currency_user -d currency_db -c "ANALYZE;"

# Vacuum tables
docker exec -it postgres psql -U currency_user -d currency_db -c "VACUUM ANALYZE;"

# Check for bloated tables
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT schemaname, tablename, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / (n_dead_tup + n_live_tup)::numeric * 100, 2) as dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 0
ORDER BY dead_pct DESC;"
```

### Exchange Rate Data Management

#### Update Exchange Rates

```bash
# Regenerate demo data with fresh rates
poetry run python scripts/generate_demo_data.py

# Check rate update timestamp
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT currency_code, rate, last_updated
FROM exchange_rates
ORDER BY last_updated DESC;"

# Verify rate consistency
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT currency_code, rate
FROM exchange_rates
WHERE rate <= 0 OR rate IS NULL;"
```

#### Validate Rate Data Integrity

```bash
# Check for missing base currency (USD should always be 1.0)
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT * FROM exchange_rates WHERE currency_code = 'USD';"

# Verify all supported currencies exist
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT COUNT(DISTINCT currency_code) as currency_count
FROM exchange_rates;"

# Check historical data completeness
docker exec -it postgres psql -U currency_user -d currency_db -c "
SELECT currency_code, COUNT(*) as history_count,
       MIN(date) as oldest_date, MAX(date) as newest_date
FROM historical_rates
GROUP BY currency_code
ORDER BY currency_code;"
```

### Service Deployment & Rollback

#### Deploy New Version

```bash
# Pull latest changes
git pull origin main

# Rebuild containers
make rebuild

# Verify deployment
curl -f http://localhost:8000/health
curl -f http://localhost:8000/api/v1/rates | jq .

# Check logs for errors
docker logs currency-api --tail=20
```

#### Rollback Procedure

```bash
# Check current commit
git log --oneline -5

# Identify last known good commit
git log --oneline -10

# Rollback to specific commit
git checkout <last_good_commit>

# Rebuild with previous version
make rebuild

# Verify rollback
curl -f http://localhost:8000/health
docker logs currency-api --tail=10
```

### Container Management

#### Service Restart Procedures

```bash
# Graceful restart (recommended)
docker restart currency-api

# Force restart if unresponsive
docker kill currency-api
docker start currency-api

# Full stack restart
make down
make up
```

#### Container Health Monitoring

```bash
# Check container status
docker ps | grep -E "(currency|postgres|prometheus|grafana)"

# Check container resource usage
docker stats --no-stream

# Check container logs
docker logs currency-api --tail=50 -f
docker logs postgres --tail=20
docker logs prometheus --tail=20
docker logs grafana --tail=20
```

#### Cleanup Procedures

```bash
# Remove old/dangling images
docker image prune -f

# Clean up unused volumes
docker volume prune -f

# Clean up unused networks
docker network prune -f

# Full cleanup (use with caution)
docker system prune -f
```

### Log Management

#### Log Collection

```bash
# Collect logs from all services
mkdir -p logs/$(date +%Y%m%d_%H%M%S)
docker logs currency-api > logs/$(date +%Y%m%d_%H%M%S)/currency-api.log 2>&1
docker logs postgres > logs/$(date +%Y%m%d_%H%M%S)/postgres.log 2>&1
docker logs prometheus > logs/$(date +%Y%m%d_%H%M%S)/prometheus.log 2>&1
docker logs grafana > logs/$(date +%Y%m%d_%H%M%S)/grafana.log 2>&1
```

#### Log Analysis

```bash
# Search for errors in application logs
docker logs currency-api --since=1h | grep -i error

# Search for specific error patterns
docker logs currency-api --since=30m | grep -E "(500|timeout|connection|database)"

# Check authentication failures
docker logs currency-api --since=1h | grep -E "(401|403|unauthorized|forbidden)"

# Analyze request patterns
docker logs currency-api --since=1h | grep -E "(GET|POST)" | awk '{print $1}' | sort | uniq -c | sort -nr
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
# Check response time distribution
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.50,%20sum(rate(http_request_duration_seconds_bucket%5B5m%5D))%20by%20(le))' | jq '.data.result[0].value[1]'
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.90,%20sum(rate(http_request_duration_seconds_bucket%5B5m%5D))%20by%20(le))' | jq '.data.result[0].value[1]'
curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.99,%20sum(rate(http_request_duration_seconds_bucket%5B5m%5D))%20by%20(le))' | jq '.data.result[0].value[1]'

# Check endpoint-specific metrics
curl -s http://localhost:8000/metrics | grep http_requests_total | grep -E "(convert|rates|health)"

# Check error rates by endpoint
curl -s http://localhost:8000/metrics | grep http_requests_total | grep status_code
```

### Troubleshooting Common Issues

#### "Service Unavailable" Errors

1. **Check container status:**

   ```bash
   docker ps | grep currency-api
   docker logs currency-api --tail=20
   ```

2. **Verify port binding:**

   ```bash
   netstat -tlnp | grep :8000
   docker port currency-api
   ```

3. **Test direct container access:**

   ```bash
   docker exec currency-api curl -f http://localhost:8000/health
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
