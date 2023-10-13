#!/usr/bin/env python

import logging
from typing import Any

from .custom_types import AuthorDetails, MinimalPaperDetails
from .search import _get_keywords

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


def _get_title(data: dict[str, Any]) -> str:
    return data["teiHeader"]["fileDesc"]["sourceDesc"]["biblStruct"]["analytic"][
        "title"
    ]["#text"]


def _get_authors(data: dict[str, Any]) -> list[AuthorDetails]:
    authors = []
    authors_list_data = data["teiHeader"]["fileDesc"]["sourceDesc"]["biblStruct"][
        "analytic"
    ]["author"]
    for author_data in authors_list_data:
        authors.append(
            AuthorDetails(
                name_parts=[
                    author_data["persName"]["forename"]["#text"],
                    author_data["persName"]["surname"],
                ],
                email=author_data["email"],
                affiliation=author_data["affiliation"]["orgName"]["#text"],
            )
        )

    return authors


def _get_abstract(data: dict[str, Any]) -> str:
    return data["teiHeader"]["profileDesc"]["abstract"]["div"]["p"]


def parse_grobid_data(
    grobid_data: dict[str, Any],
) -> MinimalPaperDetails:
    """
    Parse GROBID data into a bit more useful form.

    Parameters
    ----------
    grobid_data: Dict[str, Any]
        The data returned from GROBID after processing a PDF.

    Returns
    -------
    MinimalPaperDetails
        The parsed GROBID data.
    """
    # Construct keyword content
    title = _get_title(grobid_data)
    abstract = _get_abstract(grobid_data)
    keywords = _get_keywords(f"{title}\n\n{abstract}")

    # Parse
    return MinimalPaperDetails(
        title=title,
        authors=_get_authors(grobid_data),
        abstract=abstract,
        keywords=keywords,
    )
