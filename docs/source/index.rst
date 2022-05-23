.. PyCardano documentation master file, created by
   sphinx-quickstart on Wed Dec 29 20:36:02 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

PyCardano
=====================================

PyCardano is a standalone Cardano client written in Python. The library is able to create and sign transactions
without depending on third-party Cardano serialization tools, such as cardano-cli and cardano-serialization-lib,
making it a light-weight library that is easy and fast to set up in all kinds of environments.

.. toctree::
    :maxdepth: 1
    :caption: Get Started

    tutorial

.. toctree::
    :maxdepth: 1
    :caption: Usage Guides

    guides/address
    guides/serialization
    guides/instance_creation
    guides/transaction


.. toctree::
   :maxdepth: 1
   :caption: API Reference

   api/pycardano.address
   api/pycardano.backend.base
   api/pycardano.certificate
   api/pycardano.coinselection
   api/pycardano.exception
   api/pycardano.hash
   api/pycardano.key
   api/pycardano.metadata
   api/pycardano.nativescript
   api/pycardano.network
   api/pycardano.plutus
   api/pycardano.serialization
   api/pycardano.transaction
   api/pycardano.utils
   api/pycardano.witness


Links
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* `Github Home Page <https://github.com/cffls/pycardano>`_
* `More usage examples on Github <https://github.com/cffls/pycardano/tree/main/examples>`_

