import re
import sys
import os.path
from setuptools import setup, find_packages


ROOT = os.path.dirname(__file__)
README = open(os.path.join(ROOT, 'README')).read()
INIT_PY = open(os.path.join(ROOT, 'flask_flatpages', '__init__.py')).read()
VERSION = re.search("VERSION = '([^']+)'", INIT_PY).group(1)


setup(
    name='Flask-FlatPages',
    version=VERSION,
    url='https://github.com/SimonSapin/Flask-FlatPages',
    license='BSD',
    author='Simon Sapin',
    author_email='simon.sapin@exyr.org',
    description='Provides flat static pages to a Flask application',
    long_description=README,
    packages=find_packages(),
    # test pages
    package_data={'': ['pages*/*.*', 'pages/*/*.*', 'pages/*/*/*.*']},
    test_suite='flask_flatpages.tests',
    zip_safe=False,
    platforms='any',
    install_requires=[
        'Flask',
        'PyYAML',
        # Markdown 2.2.0 is broken on Python 2.5:
        # https://github.com/waylan/Python-Markdown/issues/113
        # Change this back to just "Markdown" when a fix for this
        # is released on PyPI.
        'Markdown' if sys.version_info >= (2, 6) else 'Markdown==2.1.1',
    ],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
    ]
)
