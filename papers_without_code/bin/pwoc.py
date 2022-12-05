#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback
from pathlib import Path
from typing import Dict, List

from papers_without_code import grobid, processing

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
                "Papers without Code: find code repositories for academic papers."
            ),
        )
        p.add_argument(
            "pdf_path",
            type=Path,
            help="Path to the PDF file to find related repositories for.",
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


def _pwoc(pdf_path: Path, teardown: bool) -> List[Dict]:
    # Create GROBID server and client for parsing PDF
    client, container = grobid.setup_or_connect_to_server()
    if client is None:
        if teardown:
            log.error(
                "Something went wrong during GROBID server setup, "
                "stopping and removing container."
            )
            grobid.teardown_server(container)
            raise EnvironmentError()
        else:
            log.error("Something went wrong during GROBID server setup.")
            raise EnvironmentError()

    # Process the PDF
    try:
        grobid_data = grobid.process_pdf(client, pdf_path=pdf_path)
    except Exception as e:
        if teardown:
            log.error(
                f"Something went wrong during GROBID PDF parsing (Error: '{e}'), "
                f"stopping and removing container."
            )
            grobid.teardown_server(container)
            raise EnvironmentError()
        else:
            log.error(f"Something went wrong during GROBID PDF parsing (Error: '{e}').")
            raise EnvironmentError()

    # Shut down server
    # We don't need it anymore
    if teardown:
        grobid.teardown_server(container)

    # Parse GROBID data
    parse_results = processing.parse_grobid_data(grobid_data)
    print(parse_results)

    # Warn user that server is still live
    if not teardown:
        log.info(
            "GROBID PDF parsing server is still alive to "
            "save time during next `pwoc` usage. "
            "You can tear it down later with `pwoc-server --shutdown`."
        )

    return []


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
        _pwoc(args.pdf_path, args.teardown)
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
