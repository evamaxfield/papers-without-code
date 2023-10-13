# [START cloudrun_paperswithoutcode_dockerfile]
# [START run_paperswithoutcode_dockerfile]

# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

# Install git and tree
RUN apt-get -y update && apt-get -y install git

# Install dependencies.
RUN pip install --no-cache-dir .

# Download / pre-cache model
RUN python scripts/cache-sentence-transformers-model.py

# Run the web server on startup
CMD pwoc-web-app

# [END run_paperswithoutcode_dockerfile]
# [END cloudrun_paperswithoutcode_dockerfile]
