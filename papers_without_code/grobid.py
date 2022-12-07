#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import docker
import requests
import xmltodict
from grobid_client.grobid_client import GrobidClient

from .custom_types import PathLike

###############################################################################

log = logging.getLogger(__name__)

###############################################################################

DEFAULT_GROBID_IMAGE = "lfoppiano/grobid:0.7.2"
DEFAULT_GROBID_PORT = 8070

###############################################################################


def setup_or_connect_to_server(
    image: Optional[str] = None,
    port: Optional[int] = None,
    grobid_client_kws: Dict[str, Any] = {"timeout": 120},
) -> Tuple[Optional[GrobidClient], docker.models.containers.Container]:
    """
    Setup (or connect to) a GROBID server managed via a local Docker container.

    Parameters
    ----------
    image: Optional[str]
        The Docker image name to use for pulling (if needed)
        and creating the container.
        Default: None (check environment variables
        for GROBID_IMAGE or else use default image)
    port: Optional[int]
        The port to make available on the GROBID server and Docker container.
        Default: None (check environment variables
        for GROBID_PORT or else use default default port)
    grobid_client_kws: Dict[str, Any]
        Any extra GROBID client keyword arguments to pass to client initialization.
        Default: {"timeout": 120}

    Returns
    -------
    Optional[GrobidClient]
        If all setup and/or connection was successful, the GROBID client connection.
        None if something went wrong.
    docker.models.containers.Container
        The Docker container object for future management.
    """
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
    docker_client = docker.from_env()

    # Check if the image is already downloaded
    try:
        docker_client.images.get(image)
    except docker.errors.ImageNotFound:
        log.info(
            f"Pulling GROBID image: '{image}' "
            f"(this will only happen the first time you run Papers without Code)."
        )
        docker_client.images.pull(image)

    # Check for already running image
    # Connect or start again
    found_running_grobid_image = False
    for container in docker_client.containers.list():
        if container.image.tags[0] == DEFAULT_GROBID_IMAGE:
            if container.status == "running":
                found_running_grobid_image = True
                break
            else:
                log.debug(
                    f"Found stopped GROBID container "
                    f"('{container.short_id}') -- Starting."
                )
                container.start()
                time.sleep(5)
                found_running_grobid_image = True
                break

    # Start new container
    if not found_running_grobid_image:
        log.info("Setting up PDF parsing server.")
        log.debug(f"Using GROBID image: '{image}'.")
        container = docker_client.containers.run(
            image,
            ports={"8070/tcp": port},
            detach=True,
        )
        log.debug(f"Started GROBID container: '{container.short_id}'.")
        time.sleep(5)

    # Attempt to connect with client
    try:
        # Make request to check the server is alive
        server_url = f"http://127.0.0.1:{port}"
        response = requests.get(f"{server_url}/api/isalive")
        response.raise_for_status()
        log.debug(f"GROBID API available at: '{server_url}'.")

        # Create a GROBID Client
        grobid_client = GrobidClient(
            grobid_server=f"http://localhost:{port}",
            check_server=False,
            **grobid_client_kws,
        )

        return grobid_client, container

    except Exception as e:
        log.error(f"Failed to connect to GROBID server, error: '{e}'.")
        return None, container


def teardown_server(
    container: docker.models.containers.Container,
) -> None:
    """
    Stop and remove a Docker container.

    Parameters
    ----------
    container: docker.models.containers.Container
        The docker container to stop and remove.
    """
    # Stop the container
    container.stop()
    container.remove()
    log.info(f"Stopped and removed Docker container: '{container.short_id}'.")


def process_pdf(
    client: GrobidClient,
    pdf_path: PathLike,
) -> Dict[str, Any]:
    """
    Process a PDF file using a GROBID client.

    Parameters
    ----------
    client: GrobidClient
        A GROBID client to use for processing.
    pdf_path: PathLike
        The path to the local PDF file to process.

    Returns
    -------
    Dict[str, Any]
        Paper data.

    Raises
    ------
    ValueError
        Something went wrong during processing.
    """
    # Convert to Path
    pdf_path = Path(pdf_path)
    pdf_path = pdf_path.resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"Provided file does not exist: '{pdf_path}'")
    if pdf_path.is_dir():
        raise IsADirectoryError(
            f"Parsing currently only supports single files. "
            f"Provided path is a directory: '{pdf_path}'"
        )

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
