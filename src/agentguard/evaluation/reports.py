"""Report helpers for benchmark and demo output."""

from agentguard.core.models import DemoReport, MetricReport


def build_demo_report(title: str, summary: str, metrics: dict | None = None) -> DemoReport:
    metric_report = MetricReport.model_validate(metrics) if metrics else None
    return DemoReport(title=title, summary=summary, metrics=metric_report)

