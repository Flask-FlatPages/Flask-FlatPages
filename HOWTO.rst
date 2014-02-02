==================
Developer’s How To
==================

Tools
=====

Optional, for testing:

    $ pip install -r testapp/requirements.txt

For releasing:

    $ pip install Sphinx Sphinx-PyPI-upload tox

Running tests
=============

Just:

    $ make -C testapp/ test

Making a new release
====================

* Update check MANIFEST.in and package_data in setup.py if non-Python files
  were added.
* Update install_requires in setup.py if dependencies changed.
* Check that tests pass in all supported Python versions (2.6, 2.7 and 3.3;
  PyPY if you like.) tox can do this automatically, assuming that the
  interpreters are installed:

      $ tox

* Bump the version number in flask_flatpages.py
* Update the docs and changelog in docs/index.rst
* Rebuild the docs, check that _build/html/index.html looks good:

      $ python setup.py build_sphinx

* Make and upload the release archive:

      $ python setup.py sdist upload upload_sphinx

* Tag the release and push to GitHub:

      $ git tag v0.X  # Same version number as in flask_flatpages.py
      $ git push
      $ git push --tags
