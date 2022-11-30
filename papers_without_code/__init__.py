# -*- coding: utf-8 -*-

"""Top-level package for papers_without_code."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("papers-without-code")
except PackageNotFoundError:
    __version__ = "uninstalled"

__author__ = "Eva Maxfield Brown"
__email__ = "evamaxfieldbrown@gmail.com"

__all__ = [
    "__author__",
    "__email__",
    "__version__",
]
