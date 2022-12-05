# A Multi-step Example for the Argo backend.
This example covers the usage of the Argo backend which allows for PIRlib pipelines to execute on Kubenetes as Argo Workflows. 

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

## Running the example
```bash
bash example/run_argo.sh
```
from the root directory of this repository.

You should be able to see the live execution of the different steps of the pipeline in the browser. The resultant files will be generated in the `outputs/` directory. The `Worflow` execution should also be visible on the browser.
