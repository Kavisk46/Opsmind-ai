from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def get_metrics() -> Response:
    """Exposes every counter/histogram recorded in core/metrics.py in
    Prometheus's text exposition format — the same format a real
    Prometheus server would `scrape` (poll) this endpoint for on an
    interval, storing each sample as a time series it can later query
    and Grafana can chart. No new infrastructure needed to produce this
    format; prometheus-client (already installed) renders it directly
    from the Counter/Histogram objects already being updated by
    main.py's middleware on every request.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
