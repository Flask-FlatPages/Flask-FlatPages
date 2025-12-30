########################
Contribution Guidelines
#######################

Flask-Flatpages welcomes any and all contributions. This file
documents the tools and conventions we use, and steps to take when submitting
a Pull-Request.

************
Tools
************

We use ``tox`` as a general-purpose tool for automating style-checking,
testing and building documentation of the project. So in principle,
contributing is as simple as

``python -m pip install tox``

and opening your editor of choice.

Linting and Style
=================

We use ``ruff`` to ensure code in the project conforms to a common
style. The config can be found in ``pyproject.toml``.

To check the style of any contributions, simply run ``tox -e lint``.

Code is linted as part of the CI pipeline, which runs on push and on opening a pull request.

Auto-formatting is handled using ruff, and can be run using ``tox -e fmt``.

Tests
=====

Any contributions to Flask-Flatpages will require corresponding test cases. Tests can be found
in the ``tests`` directory in the project root. We use classes to define groups of related tests,
and ``pytest`` as the test runner. Common fixtures can be found in `conftest.py`.

To run the full test suite, simply run ``tox``, which will test against all supported
Python versions present on your machine.

Documentation and Release Notes
===============================

All modules and functions are documented using Python docstrings, and documentation
is then generated using Sphinx.

The project documentaiton is a single-page using the ``flask`` theme. General descriptions
of the project and its operation are contained in ``docs/index.rst``. The API seciton
of the documentation is generated automatically using `autodoc <https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html>`_.

Similarly, the Changelog is automatically generated using `reno <https://docs.openstack.org/reno/latest/user/index.html>`_. When opening a pull request, please create a new
release note by running::

tox -e reno new <your-note-name-here>

And then editing the resulting file in ``releasenotes/notes``.


Documentation can be built locally using ``tox -e docs``. A live copy of the
documentation, based on the master branch, is hosted at
`ReadTheDocs <flask-flatpages.readthedocs.io>`_.

*************
PR Checklist
*************

+ Is the code linted with ``tox -e lint``?

+ Are appropriate tests added? Do they pass with ``tox``?

+ Does the PR need a release note? Include one with ``reno``, via ``tox -e reno -- new``.

+ Has the code been formatted? Check with ``tox -e fmt -- --check .``


*************
Releasing
*************

Releases are automatically handled using a Github Actions pipeline
defined in ``.github/workflows/release.yml``. To make a relase

1. Update the version in `flask_flatpages/__init__.py`. ``reno`` can help to generate the
   next version using::

     tox -e reno -- -q semver-next

2. Commit the changes, and tag the commit e.g.::

   git add flask_flatpages/__init__.py && git commit && git tag v$(reno -q semver-next)

3. Push the tag and commit to the master branch
