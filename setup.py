# -*- coding: utf-8 -*-

from os.path import join
from os.path import dirname
from setuptools import setup, find_packages

version = "1.0.0"

with open(join(dirname(__file__), "docs", "README.rst")) as f:
    long_description = f.read()

with open(join(dirname(__file__), "docs", "CHANGES.md")) as f:
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
    url="senaite/senaite.ldap",
    license="GPLv2",
    packages=find_packages("src"),
    package_dir={"": "src"},
    namespace_packages=["senaite"],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "senaite.lims",
        "python-ldap==3.3.1",
        "pas.plugins.ldap==1.8.2",
        "yafowil==3.1.1",
        "yafowil.plone==4.0.0a4",
        "pyasn1==0.4.8",
        "pyasn1-modules==0.2.8",
        "node.ext.ldap==1.2",
        "bda.cache==1.3.0",
        "node==1.2",
        "odict==1.9.0",
        "passlib==1.7.4",
        "python-memcached==1.59",
        "webresource==1.2",
        "yafowil.widget.array==1.7",
        "yafowil.widget.dict==1.8",
        "yafowil.yaml==2.0",
        "setuptools",
    ],
    extras_require={
        "test": [
            "Products.PloneTestCase",
            "Products.SecureMailHost",
            "plone.app.testing",
            "unittest2",
        ]
    },
    entry_points="""
      # -*- Entry points: -*-
      [z3c.autoinclude.plugin]
      target = plone
      """,
)
