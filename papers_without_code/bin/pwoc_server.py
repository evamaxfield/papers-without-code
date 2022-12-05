#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import sys
import traceback

import docker

from papers_without_code.grobid import (
    DEFAULT_GROBID_IMAGE,
    setup_or_connect_to_server,
    teardown_server,
)

###############################################################################

log = logging.getLogger(__name__)

###############################################################################


class Args(argparse.Namespace):
    def __init__(self) -> None:
        self.__parse()

    def __parse(self) -> None:
        p = argparse.ArgumentParser(
            prog="pwoc-server",
            description=(
                "Papers without Code: GROBID server management. "
                "Useful to start a server once then process a bunch of PDFs "
                "rather than repeated starting and stopping."
            ),
        )
        p.add_argument(
            "--start",
            action="store_true",
            help="Start a GROBID server.",
        )
        p.add_argument(
            "--stop",
            action="store_true",
            help="Stop a GROBID server.",
        )
        p.add_argument(
            "--shutdown",
            action="store_true",
            help="Shutdown and remove all GROBID servers.",
        )
        p.add_argument(
            "--debug",
            dest="debug",
            action="store_true",
            help="Run with debug logging.",
        )
        p.parse_args(namespace=self)


def _pwoc_server(start: bool, stop: bool, shutdown: bool) -> None:
    # They can't both be true
    if start and shutdown:
        raise ValueError(
            "Choose one of start, stop, or shutdown. Cannot use more than one."
        )

    # Start
    if start:
        setup_or_connect_to_server()
        return

    # Just stop
    if stop:
        docker_client = docker.from_env()
        for container in docker_client.containers.list(all=True):
            if container.image.tags[0] == DEFAULT_GROBID_IMAGE:
                container.stop()
                log.info(f"Stopped Docker container: '{container.short_id}'.")
        return

    # Teardown all
    if shutdown:
        docker_client = docker.from_env()
        for container in docker_client.containers.list(all=True):
            if container.image.tags[0] == DEFAULT_GROBID_IMAGE:
                teardown_server(container)
        return


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
        _pwoc_server(args.start, args.stop, args.shutdown)
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
