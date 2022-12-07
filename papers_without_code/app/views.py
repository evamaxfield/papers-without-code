#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

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

from ..search import (
    DEFAULT_LOCAL_CACHE_MODEL,
    DEFAULT_TRANSFORMER_MODEL,
    get_paper,
    get_repos,
)
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
    except ValueError:
        return render_template("search-doi-not-found.html", query=query)

    return render_template(
        "search-success.html",
        query=query,
        title=paper_details.title,
        paper_url=paper_details.url,
    )


@views.route("/process", methods=["POST"])
def process() -> Response:
    from keybert import KeyBERT
    from sentence_transformers import SentenceTransformer

    content_type = request.headers.get("Content-Type")
    if content_type != "application/json":
        return make_response("Content-Type not supported!")

    # Unpack
    query = request.json.get("query", None)

    if not query:
        return make_response("must provide query body parameter")

    # Return to normal DOI
    paper = get_paper(query)

    # Preload models
    potential_cache_dir = Path(DEFAULT_LOCAL_CACHE_MODEL).resolve()
    if potential_cache_dir.exists():
        loaded_sent_transformer = SentenceTransformer(str(potential_cache_dir))
        loaded_keybert = KeyBERT(str(potential_cache_dir))
    else:
        loaded_sent_transformer = SentenceTransformer(DEFAULT_TRANSFORMER_MODEL)
        loaded_keybert = KeyBERT(DEFAULT_TRANSFORMER_MODEL)

    all_repo_details = get_repos(
        paper,
        loaded_keybert=loaded_keybert,
        loaded_sent_transformer=loaded_sent_transformer,
    )

    repos = [repo_details.to_dict() for repo_details in all_repo_details]
    # return make_response(jsonify({"paper-title": paper.title}), 200)
    return make_response(jsonify(repos))
