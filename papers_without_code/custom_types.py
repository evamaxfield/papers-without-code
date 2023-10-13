#!/usr/bin/env python

from dataclasses import dataclass
from pathlib import Path
from typing import Any

###############################################################################


PathLike = str | Path

###############################################################################


@dataclass
class AuthorDetails:
    name_parts: list[str]
    email: str | None
    affiliation: str | None


@dataclass
class MinimalPaperDetails:
    title: str
    authors: list[AuthorDetails]
    abstract: str
    url: str | None = None
    keywords: list[str] | None = None
    other: dict[str, Any] | None = None
