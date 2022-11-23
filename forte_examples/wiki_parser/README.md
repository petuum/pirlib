# A Complex Reader Example
This example covers the usage of Forte to parse Wikipedia dumps as a Argo workflow. 

1. PIRlib's `docerize` module is used to generate a computation graph representation of the various steps of the process along with creating a `Docker` image which has all the necessary dependencies to run the example.
2. PIRlib's `argo` backend converts the computation graph to an `Argo Workflow` YAML file.
3. Finally, the workflow is executed by `Argo`.

# Prerequisites
A `conda` envirnoment needs to be created (and activated) which contains all the dependencies to run the example, this includes both PIRlib and Forte.

## Install `PIRlib` from source
```bash
git clone git@github.com:petuum/pirlib.git
cd pirlib && pip install -e .
```

## Install `Forte` with the right dependency
```
pip install "forte[wikipedia]"
```

It should also be noted that `Kubernetes` and `Argo` needs to be installed and configured before executing the example.

# Running the example

## Configure **Docker Hub**
In order for `Argo` to have access to the docker images, a `docker registry` needs to be configured. Currently the `dockerize` module uses `Docker Hub` as the docker registry and only supports public repositories. Follow the following steps to configure `Docker Hub`:

```bash
docker login
export DOCKER_USER=<username>
export PIRLIB_REPO=<reponame>
```
Please ensure that the repository already exists under the user name in `Docker Hub`

## Start Argo server
Although this step is not a hard requirement for running the example, it's recommended because it let's the user visualize the `Workflow` in the browser.

Follow the instructions [here](https://argoproj.github.io/argo-workflows/quick-start/) and navigate your browser to `https://127.0.0.1:2746`.

## Processing the sample data
In order to test the pipeline, sample data is provided in `inputs/dbpedia_sample/` under this directory. In order to execute the example with this data, just invoke
```bash
mkdir forte_example/wiki_parser/outputs
bash forte_examples/wiki_parser/run_sample_pipeline.sh
```
from the root directory of this repository.

You should be able to see the live execution of the different steps of the pipeline in the browser. The resultant files will be generated in the `outputs/` directory.

## Processing the full data
If the previous step runs without any issues, you may now proceed to run the pipeline on the entirety of the data available. Follow the given steps:

```bash
bash data_download.sh
```
This script will take a while to execute as it downloads around 13GB of Wikipedia dumps and store them under `inputs/dbpedia_full`. Proceed to the next steps once the downloads are complete.

If you have already run the example with the sample data, you can now directly execute
```bash
rm -rf outputs/*
bash forte_examples/wiki_parser/run_full_pipeline.sh
```
from the root directory of this repository.


**Otherwise**, follow the steps for configuring `Docker Hub` and then execute
```bash
mkdir forte_example/wiki_parser/outputs
bash forte_examples/wiki_parser/run_full_pipeline.sh
```
The outputs would appear in the `outputs/` directory and the `Workflow` execution can be viewed from the browser UI.

