try:
    from slipstream._version import __version__
except ImportError:
    try:
        from importlib.metadata import version as _version

        __version__ = _version("slipstream")
    except Exception:
        __version__ = "unknown"

__all__ = ["__version__"]
