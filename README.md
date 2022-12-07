# papers-without-code

[![Build Status](https://github.com/evamaxfield/papers-without-code/workflows/CI/badge.svg)](https://github.com/evamaxfield/papers-without-code/actions)
[![Python Package Documentation](https://github.com/evamaxfield/papers-without-code/workflows/Documentation/badge.svg)](https://evamaxfield.github.io/papers-without-code)

A Python package ([and website](https://paperswithoutcode.org)) to automatically attempt to find the code associated with a paper.

[![Image of the Papers without Code web application homepage](https://raw.githubusercontent.com/evamaxfield/papers-without-code/main/docs/_static/web-landing.png)](https://paperswithoutcode.org)

---

## Installation

**Stable Release:** `pip install papers-without-code`<br>
**Development Head:** `pip install git+https://github.com/evamaxfield/papers-without-code.git`

## Python Library

From the terminal:

```bash
pip install papers-without-code

pwoc query
# or pwoc path/to/file.pdf
```

Or in Python:

```python
from papers_without_code import search_for_repos

search_for_repos("query")
# search_for_repos("path/to/file.pdf")
```

⚠️ Prior to using PWOC with a PDF you must be logged in to Docker CLI via `docker login`
because we automatically fetch, spin up, and tear down containers for processing. ⚠️

## Documentation

For full package documentation please visit [evamaxfield.github.io/papers-without-code](https://evamaxfield.github.io/papers-without-code).

[Exploratory data analysis of the dataset used for testing](https://evamaxfield.github.io/papers-without-code/eda.html)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing the code.

**MIT License**
