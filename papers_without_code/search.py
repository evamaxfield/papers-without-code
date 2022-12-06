#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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


@dataclass
class Repo:
    name: str
    url: str
    description: str


@backoff.on_exception(backoff.expo, HTTP4xxClientError)
def _search_code_with_title(paper: Paper, api: GhApi) -> Dict[str, Any]:
    return api(
        "/search/code",
        "GET",
        query=dict(
            q=f"{paper.title}",
            # q=f"{paper.title} extension:md OR extension:tex or extension:pdf",
            per_page=10,
        ),
    )


def _get_keywords_from_abstract(paper: Paper) -> List[Tuple[str, float]]:
    potential_cache_dir = Path(
        f"./sentence-transformers_{DEFAULT_TRANSFORMER_MODEL}"
    ).resolve()
    if potential_cache_dir.exists():
        model = str(potential_cache_dir)
    else:
        model = DEFAULT_TRANSFORMER_MODEL

    return KeyBERT(model).extract_keywords(
        paper.abstract,
        keyphrase_ngram_range=(1, 3),
        top_n=5,
    )


@backoff.on_exception(backoff.expo, HTTP4xxClientError)
def _search_code_with_keywords(paper: Paper, api: GhApi) -> Dict[str, Any]:
    keywords = _get_keywords_from_abstract(paper)
    just_terms_str = " ".join([word for word, _ in keywords])
    return api(
        "/search/code",
        "GET",
        query=dict(
            q=f"{just_terms_str}",
            # q=f"{paper.title} extension:md OR extension:tex or extension:pdf",
            per_page=10,
        ),
    )


def _dedupe_code_search_response(response: Dict[str, Any]) -> List[str]:
    dedupe_repos = set()
    # Unpack items
    for item in response["items"]:
        repo_details = item["repository"]
        repo_name = repo_details["name"]
        owner_name = repo_details["owner"]["login"]
        dedupe_repos.add(f"{owner_name}/{repo_name}")

    return list(dedupe_repos)


@backoff.on_exception(backoff.expo, HTTPError, max_time=60)
def _get_repo_readme_content(repo: str) -> Optional[str]:
    response = requests.get(f"https://github.com/{repo}")
    response.raise_for_status()

    soup = BeautifulSoup(response.content, "html.parser")
    readme_container = soup.find(id="readme")

    # Will be filtered out after this
    if not readme_container:
        return None

    return readme_container.text


@dataclass
class RepoAndReadme:
    repo: str
    readme: str


@dataclass
class RepoSemanticSim(DataClassJsonMixin):
    repo: str
    similarity: float


def _semantic_sim_repos(
    repos: List[RepoAndReadme],
    paper: Paper,
) -> List[RepoSemanticSim]:
    potential_cache_dir = Path(
        f"./sentence-transformers_{DEFAULT_TRANSFORMER_MODEL}"
    ).resolve()
    if potential_cache_dir.exists():
        model = SentenceTransformer(str(potential_cache_dir))
    else:
        model = SentenceTransformer("all-MiniLM-L6-v2")

    # Collapse all readmes
    semantic_sims = []
    for repo in repos:
        sem_vec_readmes = model.encode(repo.readme, convert_to_tensor=True)
        sem_vec_abstracts = model.encode(paper.abstract, convert_to_tensor=True)

        # Compute cosine-similarities
        score = util.cos_sim(sem_vec_readmes, sem_vec_abstracts).item()
        semantic_sims.append(
            RepoSemanticSim(
                repo=repo.repo,
                similarity=score,
            )
        )

    return semantic_sims


def get_repos(paper: Paper) -> List[RepoSemanticSim]:
    # Try loading dotenv
    load_dotenv()

    # Connect to API
    api = GhApi()

    # Get repos from title search
    # TODO: thread
    repos_from_title_search = _search_code_with_title(paper, api)

    # TODO: thread
    # Get keywords from abstract
    repos_from_keyword_search = _search_code_with_keywords(paper, api)

    # Dedupe from both lists
    dedupe_found_repos = list(
        set([*repos_from_title_search, *repos_from_keyword_search])
    )
    repos_with_readmes = []
    for repo in dedupe_found_repos:
        readme_text = _get_repo_readme_content(repo)
        # Filter out repos without READMEs
        # TODO: what to do here?
        if readme_text:
            repos_with_readmes.append(
                RepoAndReadme(
                    repo=repo,
                    readme=readme_text,
                )
            )

    # Get semantic sim for them all
    scores = _semantic_sim_repos(repos_with_readmes, paper)
    scores = sorted(scores, key=lambda x: x.similarity, reverse=True)

    return scores
