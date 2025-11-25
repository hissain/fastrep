# fastrep/__init__.py
"""FastRep - A CLI and web-based tool for tracking daily work activities and generating reports."""

__version__ = "2.0.8"
__author__ = "Md. Sazzad Hissain Khan"
__email__ = "hissain.khan@gmail.com"

from .database import Database
from .models import LogEntry
from .report_generator import ReportGenerator

__all__ = ["Database", "LogEntry", "ReportGenerator"]


# fastrep/__main__.py
"""Allow package to be run with python -m fastrep."""

from .cli import cli

if __name__ == '__main__':
    cli()


# fastrep/ui/__init__.py
"""FastRep Web UI module."""

from .app import create_app, main

__all__ = ["create_app", "main"]
