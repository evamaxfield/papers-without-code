#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import (
    Blueprint,
    Request,
    Response,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)

from .. import search_for_repos
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


def _escape_query(query: str) -> str:
    return query.replace("/", "&#47;").replace(":", "&#58;")


def _unescape_query(unescaped_query: str) -> str:
    return unescaped_query.replace("&#47;", "/").replace("&#58;", ":")


def _handle_search(request: Request) -> Response:
    # Get the DOI from the form
    query = request.form.get("search")

    # Paper was found, reroute to search
    return redirect(
        url_for(
            "views.search",
            q=_escape_query(query),
        )
    )


###############################################################################


@views.route("/", methods=["GET", "POST"])
def index() -> str:
    # Handle search submission
    if request.method == "POST":
        return _handle_search(request)

    return render_template("index.html")


@views.route("/search/<q>", methods=["GET", "POST"])
def search(q: str) -> str:
    # Handle new search submission
    if request.method == "POST":
        return _handle_search(request)

    # Return to normal query
    query = _unescape_query(q)

    # Get paper details
    try:
        paper_details = get_paper(query)

    # Handle no paper found with DOI
    except Exception:
        return redirect(url_for("views.not_found"))

    return render_template(
        "search-success.html",
        query=query,
        title=paper_details.title,
        paper_url=paper_details.other["full_semantic_scholar_data"].url,
    )


@views.route("/process", methods=["POST"])
def process() -> Response:
    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return make_response("Content-Type not supported!")

    # Unpack
    query = request.json.get("query", None)
    if not query:
        return make_response("must provide query body parameter")

    # Run search
    try:
        all_repo_details = search_for_repos(query)
    except Exception:
        return redirect(url_for("views.processing_error"))

    # Return as JSON
    repos = [repo_details.to_dict() for repo_details in all_repo_details]
    return make_response(jsonify(repos))


@views.route("/not-found/", methods=["GET", "POST"])
def not_found() -> str:
    # Handle search submission
    if request.method == "POST":
        return _handle_search(request)

    return render_template(
        "index.html",
        error_explanation="No Paper Found",
    )


@views.route("/processing-error", methods=["GET", "POST"])
def processing_error() -> str:
    # Handle search submission
    if request.method == "POST":
        return _handle_search(request)

    return render_template(
        "index.html",
        error_explanation="Error Processing Data",
    )
