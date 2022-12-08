# papers-without-code

[![Build Status](https://github.com/evamaxfield/papers-without-code/workflows/CI/badge.svg)](https://github.com/evamaxfield/papers-without-code/actions)
[![Python Package Documentation](https://github.com/evamaxfield/papers-without-code/workflows/Documentation/badge.svg)](https://evamaxfield.github.io/papers-without-code)

A Python package ([and website](https://paperswithoutcode.org)) to automatically attempt to find GitHub
repositories that are similar to academic papers.

[![Image of the Papers without Code web application homepage](https://raw.githubusercontent.com/evamaxfield/papers-without-code/main/docs/_static/web-landing.png)](https://paperswithoutcode.org)

---

## Installation

**Stable Release:** `pip install papers-without-code`<br>
**Development Head:** `pip install git+https://github.com/evamaxfield/papers-without-code.git`

## Usage

Provide a DOI, SemanticScholarID, CorpusID, ArXivID, ACL,
or URL from semanticscholar.org, arxiv.org, aclweb.org,
acm.org, or biorxiv.org. DOIs can be provided as is.
All other IDs should be given with their type, for example:
`doi:10.18653/v1/2020.acl-main.447`
or `CorpusID:202558505` or `url:https://arxiv.org/abs/2004.07180`.

### CLI

```bash
pip install papers-without-code

pwoc query
# or pwoc path/to/file.pdf
```

### Python

```python
from papers_without_code import search_for_repos

search_for_repos("query")
# search_for_repos("path/to/file.pdf")
```

⚠️ Prior to using PWOC with a PDF you must be logged in to Docker CLI via `docker login`
because we automatically fetch, spin up, and tear down containers for processing. ⚠️

## How it Works

In short, we pass the query on to the Semantic Scholar search service
(wrapped by [danielnsilva/semanticscholar](https://github.com/danielnsilva/semanticscholar))
which provides us basic details about the paper. We then use
[KeyBERT](https://github.com/MaartenGr/KeyBERT) to extract keywords from the paper
title and abstract. We then make multiple threaded requests to GitHub's API
for repositories which match the keywords. Once we have all the possible repositories
back, we rank them by similarity between the repository's README and the paper's
abstract (or if not available, it's title).

When using Papers without Code locally and providing a filepath, the only change to
this workflow, is keyword extraction. When local and providing a filepath,
we use [GROBID](https://github.com/kermitt2/grobid) to extract
keywords from the full text of the paper in addition to the title and abstract.

## Documentation

For full package documentation please visit [evamaxfield.github.io/papers-without-code](https://evamaxfield.github.io/papers-without-code).

[Exploratory data analysis of the dataset used for testing](https://evamaxfield.github.io/papers-without-code/eda.html)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing the code.

**MIT License**
