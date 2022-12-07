#!/usr/bin/env python
# -*- coding: utf-8 -*-

import itertools
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import List, Optional, Tuple

import backoff
import requests
from bs4 import BeautifulSoup
from dataclasses_json import DataClassJsonMixin
from dotenv import load_dotenv
from fastcore.net import HTTP4xxClientError
from ghapi.all import GhApi
from keybert import KeyBERT
from requests.exceptions import HTTPError
from semanticscholar import Paper, SemanticScholar
from sentence_transformers import SentenceTransformer, util

###############################################################################

DEFAULT_TRANSFORMER_MODEL = "allenai-specter"
DEFAULT_LOCAL_CACHE_MODEL = f"./sentence-transformers_{DEFAULT_TRANSFORMER_MODEL}"

###############################################################################


def get_paper(query: str) -> Paper:
    """
    Get a SemanticScholar API connection, get paper, return.
    """
    api = SemanticScholar()
    paper = api.get_paper(query)

    # Handle no paper found
    if len(paper.raw_data) == 0:
        raise ValueError(f"No paper found with DOI: '{query}'")

    return paper


def _get_keywords_from_abstract(
    paper: Paper,
    stop_words: Optional[str] = "english",
    model: Optional[KeyBERT] = None,
) -> List[Tuple[str, float]]:
    # Load model
    if not model:
        potential_cache_dir = Path(DEFAULT_LOCAL_CACHE_MODEL).resolve()
        if potential_cache_dir.exists():
            model = KeyBERT(str(potential_cache_dir))
        else:
            model = KeyBERT(DEFAULT_TRANSFORMER_MODEL)

    return model.extract_keywords(
        paper.abstract,
        keyphrase_ngram_range=(3, 4),
        top_n=10,
        stop_words=stop_words,
    )


def _get_keywords_from_title(
    paper: Paper,
    stop_words: Optional[str] = "english",
    model: Optional[KeyBERT] = None,
) -> List[Tuple[str, float]]:
    # Load model
    if not model:
        potential_cache_dir = Path(DEFAULT_LOCAL_CACHE_MODEL).resolve()
        if potential_cache_dir.exists():
            model = KeyBERT(str(potential_cache_dir))
        else:
            model = KeyBERT(DEFAULT_TRANSFORMER_MODEL)

    return model.extract_keywords(
        paper.title,
        keyphrase_ngram_range=(2, 4),
        top_n=5,
        stop_words=stop_words,
    )


@dataclass
class SearchQueryDataTracker:
    query_str: str
    data_from: str
    strict: bool = False


@dataclass
class SearchQueryResponse:
    query_str: str
    data_from: str
    repo_name: str
    stars: int
    forks: int
    watchers: int
    description: str


@backoff.on_exception(backoff.expo, HTTP4xxClientError)
def _search_repos(
    query: SearchQueryDataTracker, api: GhApi
) -> List[SearchQueryResponse]:
    # Make request
    if query.strict:
        response = api(
            "/search/repositories",
            "GET",
            query=dict(
                q=f'"{query.query_str}"',
                per_page=10,
            ),
        )
    else:
        response = api(
            "/search/repositories",
            "GET",
            query=dict(
                q=f"{query.query_str}",
                per_page=10,
            ),
        )

    # Dedupe and process
    dedupe_repos_strs = set()
    results = []
    # Unpack items
    for item in response["items"]:
        if not item["fork"]:
            if item["full_name"] not in dedupe_repos_strs:
                dedupe_repos_strs.add(item["full_name"])
                results.append(
                    SearchQueryResponse(
                        query_str=query.query_str,
                        data_from=query.data_from,
                        repo_name=item["full_name"],
                        stars=item["stargazers_count"],
                        forks=item["forks"],
                        watchers=item["watchers_count"],
                        description=item["description"],
                    )
                )

    return results


@dataclass
class RepoReadmeResponse:
    repo_name: str
    data_from: str
    search_query: str
    readme_text: str
    stars: int
    forks: int
    watchers: int
    description: str


@backoff.on_exception(backoff.expo, HTTPError, max_time=60)
def _get_repo_readme_content(
    repo_data: SearchQueryResponse,
) -> Optional[RepoReadmeResponse]:
    # Request repo page
    response = requests.get(f"https://github.com/{repo_data.repo_name}")
    response.raise_for_status()

    # Read README content
    soup = BeautifulSoup(response.content, "html.parser")
    readme_container = soup.find(id="readme")

    # Will be filtered out after this
    if not readme_container:
        return None

    return RepoReadmeResponse(
        repo_name=repo_data.repo_name,
        data_from=repo_data.data_from,
        search_query=repo_data.query_str,
        readme_text=readme_container.text,
        stars=repo_data.stars,
        forks=repo_data.forks,
        watchers=repo_data.watchers,
        description=repo_data.description,
    )


@dataclass
class RepoDetails(DataClassJsonMixin):
    name: str
    link: str
    data_from: str
    search_query: str
    similarity: float
    stars: int
    forks: int
    watchers: int
    description: str


def _semantic_sim_repos(
    all_repos_details: List[RepoReadmeResponse],
    paper: Paper,
    model: Optional[SentenceTransformer] = None,
) -> List[RepoDetails]:
    # Load model
    if not model:
        potential_cache_dir = Path(DEFAULT_LOCAL_CACHE_MODEL).resolve()
        if potential_cache_dir.exists():
            model = SentenceTransformer(str(potential_cache_dir))
        else:
            model = SentenceTransformer(DEFAULT_TRANSFORMER_MODEL)

    # Encode abstract once
    sem_vec_abstract = model.encode(paper.abstract, convert_to_tensor=True)

    # Collapse all readmes
    complete_repo_details = []
    for repo_details in all_repos_details:
        sem_vec_readme = model.encode(repo_details.readme_text, convert_to_tensor=True)

        # Compute cosine-similarities
        score = util.cos_sim(sem_vec_readme, sem_vec_abstract).item()
        complete_repo_details.append(
            RepoDetails(
                name=repo_details.repo_name,
                link=f"https://github.com/{repo_details.repo_name}",
                data_from=repo_details.data_from,
                search_query=repo_details.search_query,
                similarity=score,
                stars=repo_details.stars,
                forks=repo_details.forks,
                watchers=repo_details.watchers,
                description=repo_details.description,
            )
        )

    return complete_repo_details


def get_repos(
    paper: Paper,
    loaded_keybert: Optional[KeyBERT] = None,
    loaded_sent_transformer: Optional[SentenceTransformer] = None,
) -> List[RepoDetails]:
    # Try loading dotenv
    load_dotenv()

    # Connect to API
    api = GhApi()

    # Get all the queries we want to run
    title_keywords_no_stop_words = [
        SearchQueryDataTracker(
            query_str=word,
            data_from="title",
            strict=False,
        )
        for word, _ in _get_keywords_from_title(
            paper,
            model=loaded_keybert,
        )
    ]
    title_keywords_with_stop_words = [
        SearchQueryDataTracker(
            query_str=word,
            data_from="title",
            strict=True,
        )
        for word, _ in _get_keywords_from_title(
            paper,
            model=loaded_keybert,
            stop_words=None,
        )
    ]
    abstract_keywords_no_stop_words = [
        SearchQueryDataTracker(
            query_str=word,
            data_from="abstract",
            strict=False,
        )
        for word, _ in _get_keywords_from_abstract(
            paper,
            model=loaded_keybert,
        )
    ]
    abstract_keywords_with_stop_words = [
        SearchQueryDataTracker(
            query_str=word,
            data_from="abstract",
            strict=True,
        )
        for word, _ in _get_keywords_from_abstract(
            paper,
            model=loaded_keybert,
            stop_words=None,
        )
    ]

    # Reduce in case of duplicates
    all_query_datas = [
        *title_keywords_no_stop_words,
        *title_keywords_with_stop_words,
        *abstract_keywords_no_stop_words,
        *abstract_keywords_with_stop_words,
    ]
    set_queries = []
    set_query_strs = set()
    for qd in all_query_datas:
        if qd.query_str not in set_query_strs:
            set_queries.append(qd)
            set_query_strs.add(qd.query_str)

    # Create partial search func with API access already attached
    search_func = partial(_search_repos, api=api)

    # Do a bunch of threading during the search
    with ThreadPoolExecutor() as exe:
        # Find repos from GH Search
        found_repos = itertools.chain(*list(exe.map(search_func, set_queries)))

        # Combine all responses
        repos_to_parse = []
        set_repo_strs = set()
        for found_repo in found_repos:
            if found_repo.repo_name not in set_repo_strs:
                repos_to_parse.append(found_repo)
                set_repo_strs.add(found_repo.repo_name)

        # Get the README for each repo in the set
        repos_and_readmes = list(
            exe.map(
                _get_repo_readme_content,
                repos_to_parse,
            )
        )

    # Filter nones from readmes
    repos_and_readmes = [
        r_and_r for r_and_r in repos_and_readmes if r_and_r is not None
    ]

    repos = _semantic_sim_repos(repos_and_readmes, paper, model=loaded_sent_transformer)
    return sorted(repos, key=lambda x: x.similarity, reverse=True)
