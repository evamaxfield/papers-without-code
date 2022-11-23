#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from typing import Optional

import docker

###############################################################################

DEFAULT_GROBID_IMAGE = "lfoppiano/grobid:0.7.2"
DEFAULT_GROBID_PORT = 202204

###############################################################################


def setup_server(
    port: Optional[int] = None,
) -> docker.models.containers.Container:
    # Handle vars
    if port is None:
        if "GROBID_PORT" in os.environ:
            print("Using GROBID_PORT from environment vars.")
            port = int(os.environ["GROBID_PORT"])
        else:
            port = DEFAULT_GROBID_PORT

    # Connect to Docker client
    client = docker.from_env()

    # Check if the image is already downloaded
    try:
        client.images.get(DEFAULT_GROBID_IMAGE)
    except docker.errors.ImageNotFound:
        print(f"Pulling GROBID image: '{DEFAULT_GROBID_IMAGE}'")
        docker.pull(DEFAULT_GROBID_IMAGE)

    # Start container
    container = client.containers.run(
        DEFAULT_GROBID_IMAGE,
        ports={"8070/tcp": 1234},
        detach=True,
    )
    print(f"Started GROBID container: '{container.id}'")

    return container


def teardown_server(
    container: docker.models.containers.Container,
) -> None:
    # Stop the container
    container.stop()
    container.remove()
