.. pyrap documentation master file, created by
   sphinx-quickstart on Wed Dec  7 17:08:01 2016.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pyRAP!
=================

`pyRAP` is a framework for implementing extremely powerful and
beautiful web-based AJAX applications in pure Python. No HTML. No 
JavaScript. No PHP. Just pure Python. It has been designed as a 
lightweight, easy-to-use yet powerful library that makes development of
`SaaS applications <https://de.wikipedia.org/wiki/Software_as_a_Service>`_
as easy and fast as possible.

**Contact**

* `Daniel Nyga <nyga@cs.uni-bremen.de>`_
* `Mareike Picklum <mareikep@cs.uni-bremen.de>`_

What is `pyRAP`?
----------------

*Short story*: Do you know `Eclipse's RAP framework <http://www.eclipse.org/rap>`_ for writing web applications
in pure Java? It's pretty cool. `pyRAP` is an attempt to transfer the same functionality to the world of Python.

*Long story*: `pyRAP` is a client-server architecture consisting of a JavaScript component running in the
client's web browser and implementing the low-level user interaction and widget rendering functionality.
The server component is written in Python and exposes the `pyRAP` `API <https://www.wikipedia.org/wiki/Application_Programming_Interface>`_
to the programmer. The two components communicate via a `JSON <https://www.wikipedia.org/wiki/JSON>`_-based
protocol that handles creation, position and disposition of controls, event handling such as mouse events,
and styling of widgtes. It is supposed to abstract away from the very technology-centric style of writing
web apps today, which in most cases incurs a wild mixture of different technologies like `HTML <https://www.wikipedia.org/wiki/HTML>`_,
`JavaScript <https://www.wikipedia.org/wiki/JavaScript>`_, `CSS <https://www.wikipedia.org/wiki/CSS>`_, `PHP <https://www.wikipedia.org/wiki/PHP>`_
and/or `Flash <https://www.wikipedia.org/wiki/Adobe_Flash>`_. While `pyRAP` can make use of all these technologies on a low
level, it attempts to hide their specifics and peculiarities from the programmers so they can access them transparently
through a  single coherent Python interface. This makes development more function-oriented and focussed on problem solving.


Showroom
--------

The showroom contains a couple of demo applications showcasing the possibilities
that the pyRAP framework offers.


.. container:: twocol

   .. container:: leftside

      .. figure:: _static/controls-demo.png
         :width: 300pt

   .. container:: rightside

      The `pyRAP Controls Demo` demo app showcases the rich set of graphical widgets that
      `pyRAP` offers. It is at the same time supposed to serve as a reference for
      how to use them and how write web apps in with `pyRAP`. The source of the app
      is shipped with `pyRAP` and can be found in the folder ``examples/controls``.
      You can try out the controls app at

      https://www.pyrap.org/showroom/controls

.. container:: twocol

   .. container:: leftside

      .. figure:: _static/pracmln.png
         :width: 300pt

   .. container:: rightside

      `pracmln` is a artificial intelligence toolbox for statistical relational
      learning developed at the University of Bremen. It provides a web interface
      to the learning and reasoning algorithms for Markov logic networks, which
      is entirely written in `pyRAP`. For further information about `pracmln`,
      please visit the `project webpage <http://www.pracmln.org>`_.

      https://pracmln.open-ease.org

.. container:: twocol

   .. container:: leftside

      .. figure:: _static/pracapp.jpg
         :width: 300pt

   .. container:: rightside

        `PRAC` is a natural-language interpreter for robotic applications. It is
        being developed by the Institute for Artificial Intelligence  at the University
        of Bremen and can be accessed via a web interface written in `pyRAP`.
        For further infromation about `PRAC`, we refer to the project `web page <http://www.actioncores.org>`_.

      https://prac.open-ease.org



Contents:

.. toctree::
   :maxdepth: 2
   
   synopsis
   introduction
   widgets
   layouts
   advanced

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

