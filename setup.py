# -*- coding: utf-8 -*-

from os.path import join
from os.path import dirname
from setuptools import setup, find_packages

version = "2.0.0.dev0"

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
        "node.ext.ldap==1.2",
        "python-ldap==3.3.1",
        "pyasn1==0.4.8",
        "pyasn1-modules==0.2.8",
        "node==1.2",
        "odict==1.9.0",
        "bda.cache==1.3.0",
        "passlib==1.7.4",
        "python-memcached==1.59",
        # plumber >= 2.0.0 does not support Python 2.x anymore
        "plumber<2.0.0",
        "setuptools",
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
