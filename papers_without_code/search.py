#!/usr/bin/env python
# -*- coding: utf-8 -*-

from semanticscholar import Paper, SemanticScholar

###############################################################################


def get_paper(doi: str) -> Paper:
    """
    Get a SemanticScholar API connection, get paper, return.
    """
    api = SemanticScholar()
    paper = api.get_paper(doi)

    # Handle no paper found
    if len(paper.raw_data) == 0:
        raise ValueError(
            f"No paper found with DOI: '{doi}'"
        )

    return paper
