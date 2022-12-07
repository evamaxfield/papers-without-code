# list all available commands
default:
  just --list

# clean all build, python, and lint files
clean:
	rm -fr build
	rm -fr docs/_build
	rm -fr dist
	rm -fr .eggs
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	rm -fr .coverage
	rm -fr coverage.xml
	rm -fr htmlcov
	rm -fr .pytest_cache
	rm -fr .mypy_cache

# install with all deps
install:
	pip install -e .[grobid,lint,test,docs,dev]

# lint, format, and check all files
lint:
	pre-commit run --all-files

# run tests
test:
	pytest --cov-report xml --cov-report html --cov=papers_without_code papers_without_code/tests

# run lint and then run tests
build:
	just lint
	just test

# generate Sphinx HTML documentation
generate-docs:
	rm -f docs/papers_without_code*.rst
	rm -f docs/modules.rst
	mkdir -p docs/_build
	jupyter nbconvert --execute --to html data/eda.ipynb
	mv data/eda.html docs/_build
	sphinx-apidoc -o docs papers_without_code **/tests
	python -msphinx "docs" "docs/_build"

# Generate project URI for browser opening
# We replace here to handle windows paths
# Windows paths are normally `\` separated but even in the browser they use `/`
# https://stackoverflow.com/a/61991869
project_uri := if "os_family()" == "unix" {
	justfile_directory()
} else {
	replace(justfile_directory(), "\\", "/")
}

# generate Sphinx HTML documentation and serve to browser
serve-docs:
	just generate-docs
	python -mwebbrowser -t "file://{{project_uri}}/docs/_build/index.html"

# update all static files needed for web app
get-app-static:
	cd papers_without_code/app/ && npm i
	cp \
		papers_without_code/app/node_modules/@mozilla-protocol/core/protocol/css/protocol.min.css \
		papers_without_code/app/static/
	cp \
		papers_without_code/app/node_modules/@mozilla-protocol/core/protocol/css/protocol.min.css.map \
		papers_without_code/app/static/
	cp \
		papers_without_code/app/node_modules/@mozilla-protocol/core/protocol/css/protocol-components.min.css \
		papers_without_code/app/static/
	cp \
		papers_without_code/app/node_modules/@mozilla-protocol/core/protocol/css/protocol-components.min.css.map \
		papers_without_code/app/static/
	cp \
		papers_without_code/app/node_modules/@mozilla-protocol/core/protocol/js/protocol-navigation.min.js \
		papers_without_code/app/static/

# start flask web server / run pwoc-web-app
serve-app:
	pwoc-web-app

# tag a new version
tag-for-release version:
	git tag -a "{{version}}" -m "{{version}}"
	echo "Tagged: $(git tag --sort=-version:refname| head -n 1)"

# release a new version
release:
	git push --follow-tags

# update this repo using latest cookiecutter-py-package
update-from-cookiecutter:
	pip install cookiecutter
	cookiecutter gh:evamaxfield/cookiecutter-py-package --config-file .cookiecutter.yaml --no-input --overwrite-if-exists --output-dir ..


###############################################################################
# App Deployment

# get and store user
USER := if os_family() == "windows" { env_var("%USERNAME%") } else { env_var("USER") }

# Default region for infrastructures
default_region := "us-central1"
default_key := clean(join(justfile_directory(), "../.keys/pwoc-dev.json"))
default_project := "papers-without-code"

# run gcloud login
login:
  gcloud auth login
  gcloud auth application-default login

# switch active gcloud project
switch-project project=default_project:
	gcloud config set project {{project}}

# generate a service account JSON
gen-key project=default_project:
	mkdir -p {{justfile_directory()}}/.keys/
	rm -rf {{justfile_directory()}}/.keys/{{project}}.json
	gcloud iam service-accounts create {{project}} \
		--description="Dev Service Account for {{USER}}" \
		--display-name="{{project}}"
	gcloud projects add-iam-policy-binding {{project}} \
		--member="serviceAccount:{{project}}@{{project}}.iam.gserviceaccount.com" \
		--role="roles/owner"
	gcloud iam service-accounts keys create {{justfile_directory()}}/.keys/{{project}}.json \
		--iam-account "{{project}}@{{project}}.iam.gserviceaccount.com"
	@ echo "----------------------------------------------------------------------------"
	@ echo "Sleeping for one minute while resources set up"
	@ echo "----------------------------------------------------------------------------"
	sleep 60
	cp -rf {{justfile_directory()}}/.keys/{{project}}.json {{justfile_directory()}}/.keys/pwoc-dev.json
	@ echo "----------------------------------------------------------------------------"
	@ echo "Be sure to update the GOOGLE_APPLICATION_CREDENTIALS environment variable."
	@ echo "----------------------------------------------------------------------------"

# create a new gcloud project and generate a key
init project=default_project:
	gcloud projects create {{project}} --set-as-default
	echo "----------------------------------------------------------------------------"
	echo "Follow the link to setup billing for the created GCloud account."
	echo "https://console.cloud.google.com/billing/linkedaccount?project={{project}}"
	echo "----------------------------------------------------------------------------"
	just gen-key {{project}}

# build docker image locally
build-docker:
	docker build --tag pwoc-web-app {{justfile_directory()}}

# run docker image locally
run-docker:
	docker run --rm -p 9090:8080 -e PORT=8080 pwoc-web-app

# enable gcloud services
enable-services:
	gcloud services enable cloudresourcemanager.googleapis.com
	gcloud services enable cloudfunctions.googleapis.com \
		cloudbuild.googleapis.com \
		artifactregistry.googleapis.com \
		run.googleapis.com

# deploy the web app
deploy project=default_project region=default_region:
	just enable-services
	gcloud builds submit --tag gcr.io/{{project}}/paperswithoutcode
	gcloud run deploy paperswithoutcode \
		--image gcr.io/{{project}}/paperswithoutcode \
		--region {{region}} \
		--allow-unauthenticated \
		--memory 4Gi \
		--update-env-vars GITHUB_TOKEN={{env_var("GITHUB_TOKEN")}}
