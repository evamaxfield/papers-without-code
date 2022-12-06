#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from sentence_transformers import SentenceTransformer

from papers_without_code.search import DEFAULT_TRANSFORMER_MODEL

###############################################################################

if __name__ == "__main__":
    model = SentenceTransformer(
        DEFAULT_TRANSFORMER_MODEL,
        cache_folder=Path(__file__).parent.parent,
    )
