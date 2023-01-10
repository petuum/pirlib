Writing PIR Pipelines with Python
=================================

.. include-start-after

This repository is under construction.

Setup
-----

Clone the repository:

::

   $ git clone https://github.com/petuum/pirlib
   $ cd pirlib

Install dependencies:

::

   $ conda create -n pirlib python=3.8
   $ conda activate pirlib
   $ pip install -e .

Example
-------

A toy example is provided in ``examples/multi_backends/example.py``, first install its
dependencies:

::

   $ pip install -r examples/multi_backends/requirements.txt

The example can be run in four different ways:

Running the script directly:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ python examples/multi_backends/example.py

It should output the YAML representation of the example pipeline,
followed by the outputs of the pipeline itself.

Open up ``examples/multi_backends/example.py`` and see what's inside.

Running with the `pircli` command:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ bash examples/multi_backends/run_inproc.sh

This script will 

1. Run the ``pircli`` command to convert serialize the pipeline into ``example/package_inproc.yml``.

2. Run the ``pircli`` command to execute the pipeline locally, feeding in inputs from ``example/inputs`` and saving its outputs to ``example/outputs``.

Open up ``examples/multi_backends/run_inproc.sh`` and ``examples/multi_backends/package_inproc.yml`` and
see what's inside.

Running locally as a Docker workflow:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps require a existing docker installation.

::

   $ bash examples/multi_backends/run_docker.sh

This script will

1. Automatically dockerize the local environment and serialize the pipeline into ``examples/multi_backends/package_docker.yml``.

2. Generate a docker-compose workflow from the serialized pipeline and save it to ``examples/multi_backends/docker-compose.yml``.

3. Execute the generated docker-compose workflow.

Open up ``examples/multi_backends/run_docker.sh``, ``example/multi_backends/package_docker.yml``, and
``examples/multi_backends/docker-compose.yml`` and see what's inside.

Running as an Argo Workflow
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The following steps require and existing installations of Docker, Kubernetes and Argo.


In order for Argo to have access to the docker images, a docker registry needs to be configured. Currently the `dockerize` module uses Docker Hub as the docker registry and only supports public repositories. Follow the following steps to configure Docker Hub:

::

   $ docker login
   $ export DOCKER_USER=<username>
   $ export PIRLIB_REPO=<reponame>

Please ensure that the repository already exists under the user name in Docker Hub


Follow the instructions `here <https://argoproj.github.io/argo-workflows/quick-start/>`_ and navigate your browser to ``https://127.0.0.1:2746``.

Finally, execute the example.
::

   $ bash examples/multi_backends/run_argo.sh


You should be able to see the live execution of the different steps of the pipeline in the browser.
Open up ``examples/multi_backends/package_argo.yml``, ``examples/multi_backends/argo-train.yml`` and see what's inside.


A Complex Example
-----------------

This example covers the usage of Forte to parse Wikipedia dumps as an Argo workflow.

1. PIRlib's docerize module is used to generate a computation graph representation of the various steps of the process along with creating a Docker image which has all the necessary dependencies to run the example.
2. PIRlib's argo backend converts the computation graph to an Argo Workflow YAML file.
3. Finally, the workflow is executed by Argo.

Install Forte with the right dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ conda create -n pirlib-wiki-parser python=3.8 && conda activate pirlib-wiki-parser
   $ pip install "forte[wikipedia]"


Execute on sample data
^^^^^^^^^^^^^^^^^^^^^^

In order to test the pipeline, sample data is provided in inputs/dbpedia_sample/ under this directory. In order to execute the example with this data, just invoke

::

   $ mkdir examples/wiki_parser/outputs
   $ bash examples/wiki_parser/run_sample_pipeline.sh



You should be able to see the live execution of the different steps of the pipeline in the browser. The resultant files will be generated in the outputs/ directory.

Execute on the full data
^^^^^^^^^^^^^^^^^^^^^^^^

If the previous step runs without any issues, you may now proceed to run the pipeline on the entirety of the data available. Follow the given steps:

::

   $ bash data_dowload.sh

This script will take a while to execute as it downloads around 13GB of Wikipedia dumps and store them under inputs/dbpedia_full. Proceed to the next steps once the downloads are complete.

If you have already run the example with the sample data, you can now directly execute

::

   $ rm -rf examples/wiki_parser/outputs/*
   $ bash examples/wiki_parser/run_full_pipeline.sh



If you are executing the workflow on the full data without first executing on the sample data, do the following:

::

   $ mkdir examples/wiki_parser/outputs
   $ bash examples/wiki_parser/run_full_pipeline.sh

The outputs would appear in the outputs/ directory and the Workflow execution can be viewed from the browser.

TODOs
-----

- More comprehensive error checking and reporting.
- More pluggable system for input readers and output writers.
- Better thought out config file handling.
- Docker serve backend.
- Supporting factory functions that produce handlers dynamically.
- More comments and any unit tests at all.
- Packaging a pip-installable and registering to pypi.

.. image:: _static/img/Petuum.png
  :align: center
