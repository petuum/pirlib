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

A toy example is provided in ``example/example.py``, first install its
dependencies:

::

   $ pip install -r example/requirements.txt

The example can be run in three different ways:

Running the script directly:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ python example/example.py

It should output the YAML representation of the example pipeline,
followed by the outputs of the pipeline itself.

Open up ``example/example.py`` and see what's inside.

Running with the `pircli` command:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

::

   $ bash example/run_inproc.sh

This script will (1) run the ``pircli`` command to convert serialize
the pipeline into ``example/package_inproc.yml``, and then (2) run the
``pircli`` command to execute the pipeline locally, feeding in inputs
from ``example/inputs`` and saving its outputs to ``example/outputs``.

Open up ``example/run_inproc.sh`` and ``example/package_inproc.yml`` and
see what's inside.

Running locally as a Docker workflow:
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following steps require a existing docker installation.

::

   $ bash example/run_docker.sh

This script will (1) automatically dockerize the local environment and
serialize the pipeline into ``example/package_docker.yml``, (2) generate
a docker-compose workflow from the serialized pipeline and save it to
``example/docker-compose.yml``, (3) execute the generated docker-compose
workflow.

Open up ``example/run_docker.sh``, ``example/package_docker.yml``, and
``example/docker-compose.yml`` and see what's inside.

.. include-end-before

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
