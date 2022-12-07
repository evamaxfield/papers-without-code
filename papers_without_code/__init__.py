# -*- coding: utf-8 -*-

"""Top-level package for papers_without_code."""

import logging
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import List

from keybert import KeyBERT
from sentence_transformers import SentenceTransformer

from . import custom_types, processing, search

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

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


def _get_paper_from_file(
    pdf_path: custom_types.PathLike, teardown: bool = False
) -> custom_types.MinimalPaperDetails:
    from . import grobid

    # Create GROBID server and client for parsing PDF
    client, container = grobid.setup_or_connect_to_server()
    if client is None:
        if teardown:
            log.error(
                "Something went wrong during GROBID server setup, "
                "stopping and removing container."
            )
            grobid.teardown_server(container)
            raise EnvironmentError()
        else:
            log.error("Something went wrong during GROBID server setup.")
            raise EnvironmentError()

    # Process the PDF
    try:
        grobid_data = grobid.process_pdf(client, pdf_path=pdf_path)
    except Exception as e:
        if teardown:
            log.error(
                f"Something went wrong during GROBID PDF parsing (Error: '{e}'), "
                f"stopping and removing container."
            )
            grobid.teardown_server(container)
            raise EnvironmentError()
        else:
            log.error(f"Something went wrong during GROBID PDF parsing (Error: '{e}').")
            raise EnvironmentError()

    # Shut down server
    # We don't need it anymore
    if teardown:
        grobid.teardown_server(container)

    # Parse GROBID data
    parse_results = processing.parse_grobid_data(grobid_data)

    # Warn user that server is still live
    if not teardown:
        log.warning(
            "GROBID PDF parsing server is still alive to "
            "save time during next `pwoc` usage. "
            "You can tear it down later with `pwoc-server --shutdown`."
        )

    return parse_results


def search_for_repos(
    query_or_path: str, teardown: bool = False
) -> List[search.RepoDetails]:
    """
    Query for a paper then find similar GitHub repositories to that paper.

    Provide a DOI, SemanticScholarID, CorpusID, ArXivID, ACL,
    or URL from semanticscholar.org, arxiv.org, aclweb.org,
    acm.org, or biorxiv.org. DOIs can be provided as is.
    All other IDs should be given with their type, for example:
    `doi:doi:10.18653/v1/2020.acl-main.447`
    or `CorpusID:202558505` or `url:https://arxiv.org/abs/2004.07180`.

    Parameters
    ----------
    query_or_path: str
        The structured paper to query for or a path to a file to parse.

    Returns
    -------
    List[search.RepoDetails]
        A list of repositories that are similar to the paper,
        sorted by each repositories README's semantic similarity
        to the abstract (or title if no abstract was attached to the paper details).

    Raises
    ------
    ValueError
        No paper found matching query.

    See Also
    --------
    get_paper
        The function used to query for matching papers.
    get_repos
        The function used to find and rank GitHub repositories by their similarity
        to the paper.
    """
    # Check if path and get paper details from GROBID
    if Path(query_or_path).resolve().exists():
        paper = _get_paper_from_file(query_or_path, teardown)
    # Get paper details from query
    else:
        paper = search.get_paper(query_or_path)

    # Preload models
    potential_cache_dir = Path(search.DEFAULT_LOCAL_CACHE_MODEL).resolve()
    if potential_cache_dir.exists():
        loaded_sent_transformer = SentenceTransformer(str(potential_cache_dir))
        loaded_keybert = KeyBERT(str(potential_cache_dir))
    else:
        loaded_sent_transformer = SentenceTransformer(search.DEFAULT_TRANSFORMER_MODEL)
        loaded_keybert = KeyBERT(search.DEFAULT_TRANSFORMER_MODEL)

    return search.get_repos(
        paper,
        loaded_keybert=loaded_keybert,
        loaded_sent_transformer=loaded_sent_transformer,
    )
