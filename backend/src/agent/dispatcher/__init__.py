"""
Dispatcher package exports.
"""


def dispatch(*args, **kwargs):
    from .node import dispatch as _dispatch

    return _dispatch(*args, **kwargs)


__all__ = ["dispatch"]
