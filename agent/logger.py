import structlog


def get_logger(name: str):
    """
    Return a structlog logger bound to the given module name.
    All LLM adapters and services call this — never import structlog directly.
    """
    return structlog.get_logger(name)
