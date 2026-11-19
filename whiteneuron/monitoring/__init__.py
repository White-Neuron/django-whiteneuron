

def beat(name, info=""):
    """Record that background job ``name`` just ran (see ``whiteneuron.monitoring.heartbeats``).

    Never raises. Only names listed in ``WN_HEARTBEATS`` are recorded."""
    from .heartbeats import beat as _beat

    return _beat(name, info)
