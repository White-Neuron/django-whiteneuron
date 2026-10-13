def can_view_dashboard(request):
    """Sidebar/app-mosaic permission for the monitoring dashboard (same rule as the views)."""
    return request.user.has_perm("monitoring.view_metricsample")
