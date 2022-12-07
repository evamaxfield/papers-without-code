#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

if TYPE_CHECKING:
    from pathlib import Path

###############################################################################


PathLike = Union[str, "Path"]

###############################################################################


@dataclass
class AuthorDetails:
    name_parts: List[str]
    email: Optional[str]
    affiliation: Optional[str]


@dataclass
class MinimalPaperDetails:
    title: str
    authors: List[AuthorDetails]
    abstract: str
    keywords: Optional[List[Tuple[str, float]]] = None
    other: Optional[Dict[str, Any]] = None
