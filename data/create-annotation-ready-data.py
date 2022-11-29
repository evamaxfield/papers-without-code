#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random

import numpy as np
import pandas as pd

###############################################################################
# Controlling random seeds

random.seed(202204)
np.random.seed(202204)

###############################################################################

# Read the sampled data
df = pd.read_json("data-sample.jsonl", lines=True)

# Filter by "has cs category"
df = df[df.categories.str.contains(r"(\s|^)cs\..+\s")]

# Filter by update date
# Must be more recent than Jan 1 2017
#
# Chosen because it seems like a reasonable point at which
# code sharing was starting to become adopted.
# Should look into that in the future.
# For now I am just trying to be generous.
df = df[df.update_date >= "2017-01-01"]

# Select columns of interest
df = df[["id", "doi", "update_date", "title"]]

# Select random sample
df = df.sample(50)

# Create empty columns which will be used for annotation
df["code_repository_linked_in_paper"] = None
df["code_repository_link"] = None

# Store
df.to_csv("annotation-ready.csv", index=False)