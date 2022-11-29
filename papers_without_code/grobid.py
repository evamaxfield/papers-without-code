#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import time
from typing import Any, Dict, Optional, Tuple

import docker
import requests
import xmltodict
from grobid_client.grobid_client import GrobidClient

from .types import PathLike

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

DEFAULT_GROBID_IMAGE = "lfoppiano/grobid:0.7.2"
DEFAULT_GROBID_PORT = 8070

###############################################################################


def setup_server(
    image: Optional[str] = None,
    port: Optional[int] = None,
    grobid_client_kws: Dict[str, Any] = {"timeout": 120},
) -> Tuple[Optional[GrobidClient], docker.models.containers.Container]:
    """
    # TODO
    """
    log.info("Setting up PDF parsing server")
    # Handle vars
    if image is None:
        if "GROBID_IMAGE" in os.environ:
            log.debug("Using GROBID_IMAGE from environment vars.")
            image = os.environ["GROBID_IMAGE"]
        else:
            image = DEFAULT_GROBID_IMAGE
    if port is None:
        if "GROBID_PORT" in os.environ:
            log.debug("Using GROBID_PORT from environment vars.")
            port = int(os.environ["GROBID_PORT"])
        else:
            port = DEFAULT_GROBID_PORT

    # Connect to Docker client
    client = docker.from_env()

    # Check if the image is already downloaded
    try:
        client.images.get(image)
    except docker.errors.ImageNotFound:
        log.debug(f"Pulling GROBID image: '{image}'")
        client.images.pull(image)

    # Start container
    log.debug(f"Using GROBID image: '{image}'")
    container = client.containers.run(
        image,
        ports={"8070/tcp": port},
        detach=True,
    )

    # Attempt to connect with client
    try:
        log.debug(f"Started GROBID container: '{container.id}'")
        time.sleep(5)

        # Make request to check the server is alive
        server_url = f"http://127.0.0.1:{port}"
        response = requests.get(f"{server_url}/api/isalive")
        response.raise_for_status()
        log.debug(f"GROBID API available at: '{server_url}'")

        # Create a GROBID Client
        client = GrobidClient(
            grobid_server=f"http://localhost:{port}",
            check_server=False,
            **grobid_client_kws,
        )

        return client, container

    except Exception as e:
        log.error(f"Failed to connect to GROBID server, error: {e}")
        return None, container


def teardown_server(
    container: docker.models.containers.Container,
) -> None:
    """
    # TODO
    """
    # Stop the container
    container.stop()
    container.remove()
    log.debug(f"Stopped and removed Docker container: '{container.id}'")


def process_pdf(
    client: GrobidClient,
    pdf_path: PathLike,
) -> Dict[str, Any]:
    """
    # TODO
    """
    log.info("Parsing PDF, this can sometimes take up to one minute.")
    _, status_code, result_text = client.process_pdf(
        service="processFulltextDocument",
        pdf_file=str(pdf_path),
        generateIDs=False,
        consolidate_header=True,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False,
    )

    # Handle error
    if status_code != 200 or result_text is None:
        raise ValueError(
            f"Processing failed with error: {status_code}. Error text: '{result_text}'"
            f"\nIf this issue cannot be fixed, please open a GitHub issue at: "
            f"https://github.com/evamaxfield/papers-without-code/issues/new/choose"
        )

    # Read XML
    grobid_data = xmltodict.parse(result_text)
    return grobid_data["TEI"]
