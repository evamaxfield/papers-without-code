#!/usr/bin/env python

import itertools
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial
from pathlib import Path

import backoff
import requests
from bs4 import BeautifulSoup
from dataclasses_json import DataClassJsonMixin
from dotenv import load_dotenv
from fastcore.net import HTTP4xxClientError
from ghapi.all import GhApi
from langchain import PromptTemplate
from langchain.chat_models import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain.schema import HumanMessage
from pydantic import BaseModel, Field
from requests.exceptions import HTTPError
from sentence_transformers import SentenceTransformer, util

from .custom_types import MinimalPaperDetails

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

DEFAULT_TRANSFORMER_MODEL = "thenlper/gte-small"
DEFAULT_LOCAL_CACHE_MODEL = f"./sentence-transformers_{DEFAULT_TRANSFORMER_MODEL}"

###############################################################################


def get_paper(query: str) -> MinimalPaperDetails:
    """
    Get a papers details from the Semantic Scholar API.

    Provide a DOI, SemanticScholarID, CorpusID, ArXivID, ACL,
    or URL from semanticscholar.org, arxiv.org, aclweb.org,
    acm.org, or biorxiv.org. DOIs can be provided as is.
    All other IDs should be given with their type, for example:
    `doi:doi:10.18653/v1/2020.acl-main.447`
    or `CorpusID:202558505` or `url:https://arxiv.org/abs/2004.07180`.

    Parameters
    ----------
    query: str
        The structured paper to query for.

    Returns
    -------
    Paper
        The paper details.

    Raises
    ------
    ValueErorr
        No paper was found.
    """
    log.info(f"Getting SemanticScholar paper details with query: '{query}'")
    response = requests.get(
        f"https://api.semanticscholar.org/graph/v1/paper/{query.strip()}"
        "?fields=paperId,title,authors,abstract"
    )
    response.raise_for_status()
    response_data = response.json()
    log.info(f"Found SemanticScholar paper with query: '{query}'")
    log.info(f"Response data: {response_data}")

    # Handle no paper found
    if len(response_data) == 0:
        raise ValueError(f"No paper found with DOI: '{query}'")

    return MinimalPaperDetails(
        url=f"https://www.semanticscholar.org/paper/{response_data['paperId']}",
        title=response_data.get("title"),
        authors=response_data.get("authors", None),
        abstract=response_data.get("abstract", None),
        keywords=None,
        other={"full_semantic_scholar_data": response_data},
    )


class LLMKeywordResults(BaseModel):
    keywords: list[str] = Field(
        description=("Extracted keyword sequences found in the text.")
    )


LLM_KEYWORD_RESULTS_PARSER = PydanticOutputParser(pydantic_object=LLMKeywordResults)

LLM_KEYWORD_PROMPT_STRING = (
    "Task: Create a list of five keywords from the following text. "
    "Keywords can range from one to four words in length. "
    "Only extracted text should be included in the list of keywords. "
    "Keywords can include acronyms and abbreviations.\n\n"
    "{{ format_instructions }}"
    "\n\n---\n\n"
    "Example Input Text:\n\n"
    "SciBERT: A Pretrained Language Model for Scientific Text "
    "Obtaining large-scale annotated data for NLP tasks in the "
    "scientific domain is challenging and expensive. We release SciBERT, "
    "a pretrained language model based on BERT (Devlin et. al., 2018) "
    "to address the lack of high-quality, large-scale labeled scientific data. "
    "SciBERT leverages unsupervised pretraining on a large multi-domain corpus of "
    "scientific publications to improve performance on downstream scientific "
    "NLP tasks. We evaluate on a suite of tasks including sequence tagging, "
    "sentence classification and dependency parsing, with datasets from a "
    "variety of scientific domains. We demonstrate statistically significant "
    "improvements over BERT and achieve new state-of-the-art results on several "
    "of these tasks. The code and pretrained models are available at "
    "https://github.com/allenai/scibert/."
    "\n\n---\n\n"
    "Example Output Text:\n\n"
    '{"keywords": ['
    '"SciBERT", '
    '"Language Model for Scientific Text", '
    '"large-scale labeled scientific data", '
    '"Scientific Text", '
    '"SciBERT leverages unsupervised pretraining"'
    "]}"
    "\n\n---\n\n"
    "Input Text:\n\n{{ text }}"
    "\n\n---\n\n"
)

LLM_KEYWORD_PROMPT_TEMPLATE = PromptTemplate.from_template(
    LLM_KEYWORD_PROMPT_STRING,
    template_format="jinja2",
)

backoff.on_exception(backoff.expo, exception=json.JSONDecodeError, max_time=10)


def _run_keyword_get_from_llm(text: str, llm: ChatOpenAI) -> LLMKeywordResults:
    # Fill prompt to get input
    input_ = LLM_KEYWORD_PROMPT_TEMPLATE.format_prompt(
        text=text,
        format_instructions=LLM_KEYWORD_RESULTS_PARSER.get_format_instructions(),
    )

    # Generate keywords
    output = llm([HumanMessage(content=input_.text)]).content.strip()

    # Parse output
    parsed_output = LLM_KEYWORD_RESULTS_PARSER.parse(output)

    return parsed_output


def _get_keywords(text: str) -> list[str]:
    # Create connection to LLM
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0, max_tokens=1000)

    # Get keywords
    parsed_output = _run_keyword_get_from_llm(text, llm)

    # Return keywords
    return parsed_output.keywords


@dataclass
class SearchQueryDataTracker:
    query_str: str
    strict: bool = False


@dataclass
class SearchQueryResponse:
    query_str: str
    repo_name: str
    stars: int
    forks: int
    watchers: int
    description: str


@backoff.on_exception(backoff.expo, HTTP4xxClientError)
def _search_repos(
    query: SearchQueryDataTracker, api: GhApi
) -> list[SearchQueryResponse]:
    # Make request
    if query.strict:
        response = api(
            "/search/repositories",
            "GET",
            query={
                "q": f'"{query.query_str}"',
                "per_page": 10,
            },
        )
    else:
        response = api(
            "/search/repositories",
            "GET",
            query={
                "q": f"{query.query_str}",
                "per_page": 10,
            },
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
    search_query: str
    readme_text: str
    stars: int
    forks: int
    watchers: int
    description: str


@backoff.on_exception(backoff.expo, HTTPError, max_time=60)
def _get_repo_readme_content(
    repo_data: SearchQueryResponse,
) -> RepoReadmeResponse | None:
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
    search_query: str
    similarity: float
    stars: int
    forks: int
    watchers: int
    description: str


def _semantic_sim_repos(
    all_repos_details: list[RepoReadmeResponse],
    paper: MinimalPaperDetails,
    model: SentenceTransformer | None = None,
) -> list[RepoDetails]:
    # Load model
    if not model:
        potential_cache_dir = Path(DEFAULT_LOCAL_CACHE_MODEL).resolve()
        if potential_cache_dir.exists():
            model = SentenceTransformer(str(potential_cache_dir))
        else:
            model = SentenceTransformer(DEFAULT_TRANSFORMER_MODEL)

    # Encode abstract once
    if paper.abstract:
        sem_vec_paper = model.encode(paper.abstract, convert_to_tensor=True)
    else:
        sem_vec_paper = model.encode(paper.title, convert_to_tensor=True)

    # Collapse all readmes
    complete_repo_details = []
    for repo_details in all_repos_details:
        sem_vec_readme = model.encode(repo_details.readme_text, convert_to_tensor=True)

        # Compute cosine-similarities
        score = util.cos_sim(sem_vec_readme, sem_vec_paper).item()
        complete_repo_details.append(
            RepoDetails(
                name=repo_details.repo_name,
                link=f"https://github.com/{repo_details.repo_name}",
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
    paper: MinimalPaperDetails,
    loaded_sent_transformer: SentenceTransformer | None = None,
) -> list[RepoDetails]:
    """
    Try to find GitHub repositories matching a provided paper.

    Parameters
    ----------
    paper: MinimalPaperDetails
        The paper to try and find similar repositories to.
    loaded_sent_transformer: Optional[SentenceTransformer]
        An optional preloaded SentenceTransformer model to use
        instead of loading a new one.
        Default: None

    Returns
    -------
    list[RepoDetails]
        A list of repositories that are similar to the paper,
        sorted by each repositories README's semantic similarity
        to the abstract (or title if no abstract was attached to the paper details).
    """
    # Try loading dotenv
    load_dotenv()

    # Connect to API
    api = GhApi()

    # No keywords were provided, generate from abstract and title
    if not paper.keywords:
        # Get all the queries we want to run
        if paper.title and paper.abstract:
            paper_content = f"{paper.title}\n\n{paper.abstract}"
        elif paper.title:
            paper_content = paper.title
        elif paper.abstract:
            paper_content = paper.abstract

        # Get keywords
        log.info("Right before keyword search...")
        keywords = _get_keywords(
            paper_content,
        )
        log.info("Right after keywords search...")

        # Create the queries
        set_queries = [
            SearchQueryDataTracker(
                query_str=keyword,
                strict=True,
            )
            for keyword in keywords
        ]

    # Paper was provided with keywords, use those
    else:
        set_queries = [
            SearchQueryDataTracker(
                query_str=keyword,
                strict=True,
            )
            for keyword in paper.keywords
        ]

    # Progress info
    log.info(
        f"Searching GitHub for Paper: '{paper.title}'. Using queries: {set_queries}"
    )

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
