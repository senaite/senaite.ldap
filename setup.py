# -*- coding: utf-8 -*-

from os.path import join
from os.path import dirname
from setuptools import setup, find_packages

version = "2.2.0"

with open(join(dirname(__file__), "docs", "README.rst")) as f:
    long_description = f.read()

with open(join(dirname(__file__), "docs", "CHANGES.rst")) as f:
    long_description += "\n\n"
    long_description += f.read()


setup(
    name="senaite.ldap",
    version=version,
    description="PAS Plugin for AD/LDAP",
    long_description=long_description,
    classifiers=[
        "Framework :: Plone",
        "Framework :: Zope2",
        "Programming Language :: Python",
        "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
    ],
    keywords=["senaite", "lims"],
    author="RIDING BYTES & NARALABS",
    author_email="senaite@senaite.com",
    url="https://github.com/senaite/senaite.ldap",
    license="GPLv2",
    packages=find_packages("src"),
    package_dir={"": "src"},
    namespace_packages=["senaite"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "senaite.lims",
        # PAS plugin and supporting code is vendored under
        # `senaite.ldap.pas`; we no longer depend on
        # `pas.plugins.ldap` at runtime. The YAFOWIL pins that
        # workaround its declared deps are gone with it.
        #
        # We only pin what we import directly:
        # - `node.ext.ldap` for the LDAP session, UGM layer, config
        #   schemas, scopes and property defaults.
        # - `python-ldap` for `import ldap` error constants used in
        #   `senaite.ldap.pas.plugin` (technically transitive of
        #   `node.ext.ldap`, kept explicit for pin stability).
        # - `bda.cache` for `Memcached` / `NullCache` cache providers.
        # - `python-memcached` because `browser.cache` reaches into
        #   the wrapped `memcache.Client` directly for `get_stats`
        #   (technically transitive of `bda.cache`, kept explicit).
        #
        # - `pyasn1`, `node`, `odict`, `plumber` are transitive but
        #   their newer releases are Py3-only (pyproject.toml, no
        #   setup.py) and break easy_install on Py2. Pin to the
        #   last Py2-compatible releases.
        #
        # - `pyasn1-modules` 0.4.x requires `pyasn1>=0.6.1`, so
        #   it must be pinned to a 0.2.x release that accepts our
        #   `pyasn1==0.4.8` pin.
        #
        # `passlib`, `setuptools` resolve fine as transitives.
        "node.ext.ldap==1.2",
        "python-ldap==3.3.1",
        "pyasn1==0.4.8",
        "pyasn1-modules==0.2.8",
        "node==1.2",
        "odict==1.9.0",
        "plumber==1.7",
        "bda.cache==1.3.0",
        "python-memcached==1.59",
    ],
    extras_require={
        "test": [
            "Products.PloneTestCase",
            "Products.SecureMailHost",
            "plone.app.testing",
            "unittest2",
        ],
    },
    entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
)
