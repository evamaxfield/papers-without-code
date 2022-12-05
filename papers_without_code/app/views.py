#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import (
    Blueprint,
    Request,
    Response,
    redirect,
    render_template,
    request,
    url_for,
)

from ..search import get_paper
from . import TEMPLATES_DIR

###############################################################################

views = Blueprint(
    "views",
    __name__,
    template_folder=TEMPLATES_DIR,
)

###############################################################################
# Utilities


def _escape_doi(doi: str) -> str:
    return doi.replace("/", "&#47;")


def _unescape_doi(doi: str) -> str:
    return doi.replace("&#47;", "/")


def _handle_search(request: Request) -> Response:
    # Get the DOI from the form
    search_doi = request.form.get("search")

    # Paper was found, reroute to search
    return redirect(url_for(
        "views.search",
        doi=_escape_doi(search_doi),
    ))

###############################################################################


@views.route("/", methods=["GET", "POST"])
def index():
    # Handle search submission
    if request.method == "POST":
        return _handle_search(request)

    return render_template("index.html")


@views.route("/search/<doi>", methods=["GET", "POST"])
def search(doi: str):
    # Handle new search submission
    if request.method == "POST":
        return _handle_search(request)

    # Return to normal DOI
    doi = _unescape_doi(doi)

    # Get paper details
    try:
        paper_details = get_paper(doi)

    # Handle no paper found with DOI
    except ValueError:
        return render_template("search-doi-not-found.html", doi=doi)

    return render_template("search-success.html", doi=doi, title=paper_details.title)
