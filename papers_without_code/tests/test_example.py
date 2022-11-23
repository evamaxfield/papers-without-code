#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pytest

from papers_without_code import example


@pytest.mark.parametrize(
    "string, count",
    [
        ("string", 6),
        ("hello", 5),
        ("world", 5),
        ("defenestration", 14),
    ],
)
def test_str_len(string: str, count: int) -> None:
    assert example.str_len(string) == count
