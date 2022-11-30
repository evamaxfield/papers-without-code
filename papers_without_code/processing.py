#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from typing import Any, Dict, List, Tuple

from keybert import KeyBERT

from .types import AuthorDetails, ParseResult

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


def _get_title(data: Dict[str, Any]) -> str:
    return data["teiHeader"]["fileDesc"]["sourceDesc"]["biblStruct"]["analytic"][
        "title"
    ]["#text"]


def _get_authors(data: Dict[str, Any]) -> List[AuthorDetails]:
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


def _get_abstract(data: Dict[str, Any]) -> str:
    return data["teiHeader"]["profileDesc"]["abstract"]["div"]["p"]


def _get_keywords_from_authors(data: Dict[str, Any]) -> List[str]:
    return data["teiHeader"]["profileDesc"]["textClass"]["keywords"]["term"]


def _get_paper_text(data: Dict[str, Any]) -> str:
    text_segments = []
    for div in data["text"]["body"]["div"]:
        if isinstance(div["p"], str):
            text_segments.append(div["p"])
        else:
            for para in div["p"]:
                if isinstance(para, str):
                    text_segments.append(para)
                else:
                    text_segments.append(para["#text"])

    return " ".join(text_segments)


def _get_keywords_from_bert(data: Dict[str, Any]) -> List[Tuple[str, float]]:
    # Get all the text of the paper
    text = _get_paper_text(data)

    # Pass into keybert to extract keywords
    # model = KeyBERT(model="allenai/longformer-base-4096")

    # Extract keywords
    keywords = KeyBERT().extract_keywords(text, keyphrase_ngram_range=(1, 3), top_n=5)

    return keywords


def parse_grobid_data(
    grobid_data: Dict[str, Any],
    compute_keywords_with_bert: bool = True,
) -> ParseResult:
    """
    # TODO
    """
    # Check if bert keywords are desired
    if compute_keywords_with_bert:
        bert_keywords = _get_keywords_from_bert(grobid_data)
    else:
        bert_keywords = None

    # Parse
    return ParseResult(
        title=_get_title(grobid_data),
        authors=_get_authors(grobid_data),
        abstract=_get_abstract(grobid_data),
        listed_keywords=_get_keywords_from_authors(grobid_data),
        bert_keywords=bert_keywords,
    )
