from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def wn_late_critical_heartbeats(context):
    """Late ``critical`` background jobs, for users who may view the monitoring dashboard."""
    request = context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.has_perm("monitoring.view_metricsample"):
        return []
    from whiteneuron.monitoring.heartbeats import late

    return late(critical_only=True)
