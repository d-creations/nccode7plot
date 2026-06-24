"""ncplot7py package.

Lightweight package initialiser. The package follows a clean architecture
layout: domain, application, interfaces, infrastructure, shared, and cli.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("ncplot7py")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["cli", "domain", "application", "interfaces", "infrastructure", "shared"]
