# papers-without-code

[![Build Status](https://github.com/evamaxfield/papers-without-code/workflows/CI/badge.svg)](https://github.com/evamaxfield/papers-without-code/actions)
[![Documentation](https://github.com/evamaxfield/papers-without-code/workflows/Documentation/badge.svg)](https://evamaxfield.github.io/papers-without-code)

A package (and website) to automatically attempt to find the code associated with a paper.

---

## Installation

**Stable Release:** `pip install papers-without-code`<br>
**Development Head:** `pip install git+https://github.com/evamaxfield/papers-without-code.git`

## Quickstart

From the terminal:

```bash
pip install papers-without-code

pwoc path/to/file.pdf
```

Or in Python:

```python
from papers_without_code import parse_pdf

parse_pdf("path/to/file.pdf")
```

⚠️ Prior to using PWOC you must be logged in to Docker CLI via `docker login`
because we automatically fetch, spin up, and tear down containers for processing. ⚠️

## Documentation

For full package documentation please visit [evamaxfield.github.io/papers-without-code](https://evamaxfield.github.io/papers-without-code).

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing the code.

**MIT License**
