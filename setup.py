"""
Flask-FlatPages
---------------

Provides flat static pages to a Flask_ application, based on text files
as opposed to a relationnal database.

* BSD licensed
* Latest documentation `on python.org`_
* Source, issues and pull requests `on Github`_
* Releases `on PyPI`_
* Install with ``pip install Flask-FlatPages``

.. _Flask: http://flask.pocoo.org/
.. _on python.org: http://packages.python.org/Flask-FlatPages/
.. _on Github: https://github.com/SimonSapin/Flask-FlatPages/
.. _on PyPI: http://pypi.python.org/pypi/Flask-FlatPages

"""

from setuptools import setup, find_packages

setup(
    name='Flask-FlatPages',
    version='0.2', # also change this in docs/conf.py
    url='https://github.com/SimonSapin/Flask-FlatPages',
    license='BSD',
    author='Simon Sapin',
    author_email='simon.sapin@exyr.org',
    description='Provides flat static pages to a Flask application',
    long_description=__doc__,
    packages=find_packages(),
    # test pages
    package_data={'': ['pages*/*.*', 'pages/*/*.*', 'pages/*/*/*.*']},
    test_suite='flask_flatpages.tests',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask',
        'PyYAML',
        'Markdown',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
    ]
)
