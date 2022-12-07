#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pprint import pprint

from papers_without_code import search_for_repos

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="pwoc",
            description=(
                "Papers without Code: Find GitHub repositories similar "
                "to academic papers."
            ),
        )
        p.add_argument(
            "query_or_pdf_path",
            type=str,
            help=(
                "Query or path to the PDF file to find related repositories for."
                "When providing a path, provide it as you normally would: "
                "'/path/to/file.pdf'. "
                "When providing a query such as a DOI, SemanticScholarID, "
                "CorpusID, ArXivID, ACL, "
                "or URL from semanticscholar.org, arxiv.org, aclweb.org, "
                "acm.org, or biorxiv.org. DOIs can be provided as is. "
                "All other IDs should be given with their type, for example: "
                "doi:10.1002/pra2.601 or corpusid:248266768 or "
                "url:https://arxiv.org/abs/2204.09110."
            ),
        )
        p.add_argument(
            "-t",
            "--teardown-after-done",
            action="store_true",
            dest="teardown",
            help=(
                "Teardown the created GROBID PDF parsing server "
                "after processing is complete."
            ),
        )
        p.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            help="Run with debug logging.",
        )
        p.parse_args(namespace=self)


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

    # Process
    try:
        repos = search_for_repos(
            query_or_path=args.query_or_pdf_path,
            teardown=args.teardown,
        )
        print()
        print()

        # Handle nothing found
        if len(repos) == 0:
            print("No repositories found which were similar.")

        # At least one
        else:
            print("Most Similar Repository")
            print("-----------------------")
            pprint(repos[0])

        # More
        if len(repos) > 1:
            print()
            print()
            print("Other Similar Repositories")
            print("--------------------------")
            pprint(repos[1:])

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
