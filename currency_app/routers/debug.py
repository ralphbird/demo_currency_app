"""Debug endpoints for DDoS attack investigation."""

from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from currency_app.database import get_db
from currency_app.models.database import ConversionHistory

router = APIRouter(prefix="/api/debug", tags=["debug"])


@router.get("/user-activity")
async def get_user_activity(
    minutes: int = Query(default=10, ge=1, le=60, description="Minutes to look back"),
    limit: int = Query(default=20, ge=5, le=100, description="Max users to return"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get recent user activity for DDoS investigation.

    This endpoint helps identify users with unusually high activity levels
    by analyzing conversion requests over the specified time window.

    Args:
        minutes: Number of minutes to look back (1-60)
        limit: Maximum number of users to return (5-100)
        db: Database session

    Returns:
        Dictionary with user activity statistics
    """
    # Calculate time window
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(minutes=minutes)

    # Query for user activity in the time window
    user_activity = (
        db.query(
            ConversionHistory.user_id,
            ConversionHistory.account_id,
            func.count(ConversionHistory.id).label("request_count"),
            func.min(ConversionHistory.conversion_timestamp).label("first_request"),
            func.max(ConversionHistory.conversion_timestamp).label("last_request"),
        )
        .filter(ConversionHistory.conversion_timestamp >= start_time)
        .filter(ConversionHistory.conversion_timestamp <= end_time)
        .group_by(ConversionHistory.user_id, ConversionHistory.account_id)
        .order_by(func.count(ConversionHistory.id).desc())
        .limit(limit)
        .all()
    )

    # Format results
    users = []
    total_requests = 0
    for row in user_activity:
        request_count = row.request_count
        total_requests += request_count

        # Calculate requests per minute
        time_span_minutes = max(1, (row.last_request - row.first_request).total_seconds() / 60)
        requests_per_minute = round(request_count / time_span_minutes, 2)

        users.append(
            {
                "user_id": row.user_id,
                "account_id": row.account_id,
                "request_count": request_count,
                "requests_per_minute": requests_per_minute,
                "first_request": row.first_request.isoformat(),
                "last_request": row.last_request.isoformat(),
                "time_span_minutes": round(time_span_minutes, 2),
            }
        )

    # Calculate statistics
    return {
        "time_window": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "minutes": minutes,
        },
        "summary": {
            "total_active_users": len(users),
            "total_requests": total_requests,
            "avg_requests_per_user": round(total_requests / len(users), 2) if users else 0,
        },
        "users": users,
    }


@router.get("/request-patterns")
async def get_request_patterns(
    minutes: int = Query(default=10, ge=1, le=60, description="Minutes to look back"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Analyze request patterns for anomaly detection.

    This endpoint provides insights into request patterns that might indicate
    coordinated attacks or unusual behavior.

    Args:
        minutes: Number of minutes to look back (1-60)
        db: Database session

    Returns:
        Dictionary with request pattern analysis
    """
    # Calculate time window
    end_time = datetime.now(UTC)
    start_time = end_time - timedelta(minutes=minutes)

    # Get all conversions in time window
    conversions = (
        db.query(
            ConversionHistory.user_id,
            ConversionHistory.account_id,
            ConversionHistory.from_currency,
            ConversionHistory.to_currency,
            ConversionHistory.conversion_timestamp,
        )
        .filter(ConversionHistory.conversion_timestamp >= start_time)
        .filter(ConversionHistory.conversion_timestamp <= end_time)
        .order_by(ConversionHistory.conversion_timestamp)
        .all()
    )

    if not conversions:
        return {
            "time_window": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "minutes": minutes,
            },
            "summary": {"total_requests": 0},
            "patterns": {},
        }

    # Analyze patterns
    currency_pairs = Counter()
    accounts_by_user_count = defaultdict(set)
    user_request_intervals = defaultdict(list)

    prev_timestamp = None

    for conv in conversions:
        # Count currency pairs
        currency_pairs[f"{conv.from_currency}_to_{conv.to_currency}"] += 1

        # Track accounts per user
        accounts_by_user_count[conv.user_id].add(conv.account_id)

        # Calculate request intervals
        if prev_timestamp:
            interval = (conv.conversion_timestamp - prev_timestamp).total_seconds()
            user_request_intervals[conv.user_id].append(interval)
        prev_timestamp = conv.conversion_timestamp

    # Detect suspicious patterns
    suspicious_users = []
    for user_id, intervals in user_request_intervals.items():
        if len(intervals) >= 5:  # At least 5 requests to analyze
            avg_interval = sum(intervals) / len(intervals)
            # Flag users with very consistent intervals (potential bots)
            if avg_interval < 5 and all(abs(i - avg_interval) < 2 for i in intervals):
                suspicious_users.append(
                    {
                        "user_id": user_id,
                        "request_count": len(intervals) + 1,
                        "avg_interval_seconds": round(avg_interval, 2),
                        "pattern": "consistent_timing",
                        "description": "Requests with very regular intervals (potential bot)",
                    }
                )

    return {
        "time_window": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "minutes": minutes,
        },
        "summary": {
            "total_requests": len(conversions),
            "unique_users": len(user_request_intervals),
            "unique_accounts": len({conv.account_id for conv in conversions}),
        },
        "patterns": {
            "top_currency_pairs": dict(currency_pairs.most_common(10)),
            "multi_account_users": [
                {"user_id": user_id, "account_count": len(accounts)}
                for user_id, accounts in accounts_by_user_count.items()
                if len(accounts) > 1
            ],
            "suspicious_users": suspicious_users,
        },
    }
