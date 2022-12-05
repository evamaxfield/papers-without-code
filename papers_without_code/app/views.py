#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint, render_template

from . import TEMPLATES_DIR

###############################################################################

views = Blueprint(
    "views",
    __name__,
    template_folder=TEMPLATES_DIR,
)

###############################################################################


@views.route("/")
def index():
    return render_template("index.html")
