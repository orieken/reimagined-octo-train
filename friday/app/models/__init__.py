# app/models/__init__.py

"""
Import and export models for the application via auto-discovery.

This module consolidates and exposes models from:
- Base models (enums, foundational types)
- Domain models (core business logic)
- Schema models (API request/response structures)
- Response models (HTTP API responses)
- Search and analysis models
- Database models (SQLAlchemy ORM)
"""

from . import (
    base as base_module,
    domain as domain_module,
    schemas as schemas_module,
    responses as responses_module,
    search_analysis as search_analysis_module,
    notification as notification_module,
    database as database_module
)

# Collect public symbols from all submodules
def public_symbols(module):
    return {
        name: getattr(module, name)
        for name in dir(module)
        if not name.startswith("_")
    }

# Flatten all models into global scope
globals().update(public_symbols(base_module))
globals().update(public_symbols(domain_module))
globals().update(public_symbols(schemas_module))
globals().update(public_symbols(responses_module))
globals().update(public_symbols(search_analysis_module))
globals().update(public_symbols(notification_module))
globals().update(public_symbols(database_module))

# Generate __all__ from all public symbols
__all__ = sorted(set(
    list(public_symbols(base_module).keys()) +
    list(public_symbols(domain_module).keys()) +
    list(public_symbols(schemas_module).keys()) +
    list(public_symbols(responses_module).keys()) +
    list(public_symbols(search_analysis_module).keys()) +
    list(public_symbols(notification_module).keys()) +
    list(public_symbols(database_module).keys())
))
