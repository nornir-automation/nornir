.. nornir documentation master file, created by
   sphinx-quickstart on Sun Nov 19 10:41:40 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to nornir's documentation!
===================================

.. image:: _static/logo/nornir_logo_02.jpg
   :height: 500px
   :width: 500px

Nornir is an automation framework written in python to be used with python. Most automation
frameworks hide the language they are written in by using some cumbersome pseudo-language
which usually is almost Turing complete, but lacks tooling to debug and troubleshoot. Integrating
with other systems is also usually quite hard as they usually have complex APIs if any at all.
Some of the other common problems of those pseudo-languages is that are usually quite bad
at dealing with data and re-usability is limited.

Nornir aims to solve those problems by providing a pure python framework. Just imagine Nornir
as the Flask of automation. Nornir will take care of dealing with the inventory where you
have your host information, it will take care of dispatching the tasks to your devices and
will provide a common framework to write "plugins".

Nornir requires Python 3.6.2 or higher to be installed.

Contents
========

.. toctree::
   :maxdepth: 1

   Home <self>
   tutorial/index
   configuration/index
   plugins/index
   api/index
   old/index

Indices and tables

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
