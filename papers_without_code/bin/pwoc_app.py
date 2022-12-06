#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import os
import sys
import traceback

from flask import Flask

from papers_without_code.app import STATIC_DIR, views

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="pwoc-web-app",
            description="Papers without Code: Run the web application.",
        )
        p.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            help=(
                "Run with debug logging. "
                "Note: the web server is always ran in debug mode, this is for other "
                "functional logging."
            ),
        )
        p.parse_args(namespace=self)


def _pwoc_app() -> None:
    # Create
    app = Flask(
        __name__,
        static_folder=STATIC_DIR,
    )

    # Load views
    app.register_blueprint(views.views, url_prefix="/")

    # Print os.environ has GITHUB_TOKEN
    runner_has_gh_token = "GITHUB_TOKEN" in os.environ
    log.info(f"App has access to GitHub Token: {runner_has_gh_token}")

    # Run (debug allows live reloading)
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


def main() -> None:
    # Get args
    args = Args()

    # Determine log level
    if args.debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    # Setup logging
    logging.basicConfig(
        level=log_level,
        format="[%(levelname)4s: %(module)s:%(lineno)4s %(asctime)s] %(message)s",
    )

    # Manage servers
    try:
        _pwoc_app()
    except Exception as e:
        log.error("=============================================")
        log.error("\n\n" + traceback.format_exc())
        log.error("=============================================")
        log.error("\n\n" + str(e) + "\n")
        log.error("=============================================")
        sys.exit(1)


###############################################################################
# Allow caller to directly run this module (usually in development scenarios)

if __name__ == "__main__":
    main()
