"""Analytics Engine - tracks costs, tokens, performance, and quality"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record(self, metric_type: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        self._metrics[metric_type].append({
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        })

    def record_cost(self, model: str, provider: str, cost_usd: float,
                    tokens: int, task_type: str = ""):
        self.record("cost", cost_usd, {
            "model": model,
            "provider": provider,
            "tokens": tokens,
            "task_type": task_type,
        })

    def record_latency(self, operation: str, latency_ms: float,
                       success: bool = True):
        self.record("latency", latency_ms, {
            "operation": operation,
            "success": success,
        })

    def record_quality(self, content_id: str, score: float,
                       review_type: str = ""):
        self.record("quality", score, {
            "content_id": content_id,
            "review_type": review_type,
        })

    def record_content_metric(self, metric_name: str, value: float,
                              content_id: str = ""):
        self.record(metric_name, value, {"content_id": content_id})

    def get_summary(self, metric_type: str, hours: int = 24) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        records = [
            r for r in self._metrics.get(metric_type, [])
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        if not records:
            return {"count": 0, "total": 0, "average": 0, "min": 0, "max": 0}

        values = [r["value"] for r in records]
        return {
            "count": len(records),
            "total": sum(values),
            "average": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
        }

    def get_cost_breakdown(self, hours: int = 24) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        cost_records = [
            r for r in self._metrics.get("cost", [])
            if datetime.fromisoformat(r["timestamp"]) > cutoff
        ]

        by_model = defaultdict(float)
        by_provider = defaultdict(float)
        by_task = defaultdict(float)
        total = 0

        for record in cost_records:
            meta = record["metadata"]
            cost = record["value"]
            total += cost
            by_model[meta.get("model", "unknown")] += cost
            by_provider[meta.get("provider", "unknown")] += cost
            by_task[meta.get("task_type", "unknown")] += cost

        return {
            "total_cost_usd": total,
            "by_model": dict(by_model),
            "by_provider": dict(by_provider),
            "by_task": dict(by_task),
            "record_count": len(cost_records),
        }

    def get_performance_report(self, hours: int = 24) -> Dict[str, Any]:
        latency_summary = self.get_summary("latency", hours)
        cost_breakdown = self.get_cost_breakdown(hours)
        quality_summary = self.get_summary("quality", hours)

        return {
            "period_hours": hours,
            "latency": latency_summary,
            "cost": cost_breakdown,
            "quality": quality_summary,
        }


class AnalyticsEngine:
    def __init__(self, db=None):
        self.db = db
        self.collector = MetricsCollector()

    def track_generation(self, model: str, provider: str, task_type: str,
                         input_tokens: int, output_tokens: int, cost_usd: float,
                         latency_ms: float, success: bool = True):
        total_tokens = input_tokens + output_tokens
        self.collector.record_cost(model, provider, cost_usd, total_tokens, task_type)
        self.collector.record_latency(f"generation:{task_type}", latency_ms, success)

        if self.db:
            from backend.db.models import UsageRecord
            record = UsageRecord(
                model_provider=provider,
                model_name=model,
                operation=task_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                success=success,
            )
            self.db.add(record)
            self.db.commit()

    def track_content_quality(self, content_id: str, score: float,
                              review_type: str = "comprehensive"):
        self.collector.record_quality(content_id, score, review_type)

        if self.db:
            from backend.db.models import ContentAnalytics
            analytics = ContentAnalytics(
                content_id=content_id,
                metric_type="quality_score",
                metric_value=score,
                source=review_type,
            )
            self.db.add(analytics)
            self.db.commit()

    def track_seo_score(self, content_id: str, score: float):
        self.collector.record_content_metric("seo_score", score, content_id)

    def track_workflow_run(self, workflow_id: str, status: str,
                           duration_seconds: float, steps_completed: int):
        self.collector.record_content_metric("workflow_duration", duration_seconds, workflow_id)
        self.collector.record("workflow_runs", 1, {
            "workflow_id": workflow_id,
            "status": status,
            "steps_completed": steps_completed,
        })

    def get_dashboard_data(self, project_id: Optional[str] = None,
                           hours: int = 24) -> Dict[str, Any]:
        report = self.collector.get_performance_report(hours)

        if self.db:
            from backend.db.models import Content, WorkflowRun
            content_count = self.db.query(Content).filter(
                Content.project_id == project_id
            ).count() if project_id else self.db.query(Content).count()

            workflow_runs = self.db.query(WorkflowRun).filter(
                WorkflowRun.created_at > datetime.now(timezone.utc) - timedelta(hours=hours)
            ).count()

            report["content_count"] = content_count
            report["workflow_runs"] = workflow_runs
        else:
            report["content_count"] = 0
            report["workflow_runs"] = 0

        return report

    def get_usage_report(self, user_id: Optional[str] = None,
                         project_id: Optional[str] = None) -> Dict[str, Any]:
        if self.db:
            from backend.db.models import UsageRecord
            from sqlalchemy import func

            query = self.db.query(
                func.sum(UsageRecord.cost_usd).label("total_cost"),
                func.sum(UsageRecord.total_tokens).label("total_tokens"),
                func.count(UsageRecord.id).label("total_requests"),
                func.avg(UsageRecord.latency_ms).label("avg_latency"),
            )

            if user_id:
                query = query.filter(UsageRecord.user_id == user_id)
            if project_id:
                query = query.filter(UsageRecord.project_id == project_id)

            result = query.first()
            return {
                "total_cost_usd": result.total_cost or 0,
                "total_tokens": result.total_tokens or 0,
                "total_requests": result.total_requests or 0,
                "avg_latency_ms": result.avg_latency or 0,
            }

        cost_data = self.collector.get_cost_breakdown()
        return {
            "total_cost_usd": cost_data["total_cost_usd"],
            "total_tokens": sum(
                r.get("metadata", {}).get("tokens", 0)
                for r in self.collector._metrics.get("cost", [])
            ),
            "total_requests": cost_data["record_count"],
            "avg_latency_ms": self.collector.get_summary("latency").get("average", 0),
        }
