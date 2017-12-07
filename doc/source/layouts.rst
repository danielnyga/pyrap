Layout Managers
===============

GridLayout
----------

The :class:`GridLayout` is the most powerful layout manager that `pyRAP` provides. The :class:`ColumnLayout`,
:class:`RowLayout` and :class:`CellLayout` layouts are all special cases of :class:`GridLayout`. A :class:`GridLayout`
arranges all child widgets of a :class:`Composite` in a virtual grid. "Virtual" means that the individual cells
in the grid only exist logically, they do have physically existing counterpart (like DOM elements or the like). The
dimensions of the grid are determined by the number of columns or rows specified by the programmer, and the number of
children the respective :class:`Composite` holds. Consequently, a :class:`GridLayout` must be initialized with
`either` the desired number of columns (``cols``) `or` the desired number of rows (``rows``). If the number
of columns are specified, the grid will be filled with child widgets from left to right and a new row will be started
when a column is filled with ``cols`` children. Conversely, if the number of rows is specified, the grid will
be filled from top to bottom and a new column will be started when a row is filled with ``rows`` children.

The :class:`GridLayout` Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``pyrap/examples/layouts`` directory of the ``pyRAP`` repository contains an app ``gridlayout.py``,
which illustrates certain settings and possible customizations of the :class:`GridLayout`.

.. code-block:: python
   :linenos:

    def dimensions(self, **kwargs):
        rows, cols = ifnone(kwargs.get('rows'), None, int), ifnone(kwargs.get('cols'), None, int)
        shell = Shell(title='GridLayout with %s rows and %s columns' % (ifnone(rows, 'variable'), ifnone(cols, 'variable')))
        shell.content.layout = GridLayout(rows=rows, cols=cols)
        for i in range(20):
            Button(shell.content, text='Button %.2d' % (i+1))
        shell.on_resize += shell.dolayout
        shell.show(True)

The ``dimensions`` entrypoint can be called with either the number of columns (``cols=xx``) or the number of rows (``rows=xx``).
The app will create a dialog window and initialize a :class:`GridLayout` with the respective arguments, and fill
it with 20 buttons each carrying its index in the its label. The following two screenshots show the differences
in the grid layout depending on the parameters given:

.. container:: twocol

   .. container:: left

      .. figure:: _static/gridlayout-cols.png
         :height: 300pt

         ``http://localhost:8080/grid/dimensions?cols=5``

   .. container:: right

      .. figure:: _static/gridlayout-rows.png
         :height: 300pt

         ``http://localhost:8080/grid/dimensions?rows=5``

Feel free to play around with different numbers and parameterizations and how they affect the arrangement
of the buttons!

Alignment within a Grid Cell
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The child widgets of a composite with a grid layout are arranged according to the virtual grid induced by the
number of rows or columns, where each widget is placed in precisely one grid cell. Unless anything different is specified,
the layout manager will compute the dimensions of a single grid cell so it will wrap exactly around the respective
widget. However, in many cases, the surrounding grid cell is much bigger than widget it holds. This is for instance
the case when there are widgets of different heights in a single row. Then, the heights of all
grid cells in the row are determined by the highest widget, because all cells in a row must have the same
height in order to form a proper grid. In such cases the widgets can be aligned within the grid cell in different ways.
The parameters for controling the alignment behavior of single widgets in horizontal and vertical dimensions are the
``halign`` and ``valign`` parameters. The following tables summarize the behavior of different values.

+--------------+-------------------------------------------------------------------+
| Value        | Behavior                                                          |
+==============+===================================================================+
| ``'center'`` | centers the widget horizontally in the grid cell                  |
+--------------+-------------------------------------------------------------------+
| ``'left'``   | aligns the widget to the left border of the grid cell             |
+--------------+-------------------------------------------------------------------+
| ``'right'``  | aligns the widget to the right border of the grid cell            |
+--------------+-------------------------------------------------------------------+
| ``'fill'``   | Stretches the widget so it horizontally fills the whole grid cell |
+--------------+-------------------------------------------------------------------+


+--------------+-----------------------------------------------------------------+
| Value        | Behavior                                                        |
+==============+=================================================================+
| ``'center'`` | centers the widget vertically in the grid cell                  |
+--------------+-----------------------------------------------------------------+
| ``'top'``    | aligns the widget to the top border of the grid cell            |
+--------------+-----------------------------------------------------------------+
| ``'bottom'`` | aligns the widget to the bottom border of the grid cell         |
+--------------+-----------------------------------------------------------------+
| ``'fill'``   | Stretches the widget so it vertically fills the whole grid cell |
+--------------+-----------------------------------------------------------------+

Both ``halign`` and ``valign`` default to ``'center'``.

Flexible Column Widths and Row Heights
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For terminal widgets, i.e. widgets that do not
contain any other widgets as children, ``halign`` and ``valign`` are the only layout parameters required
to control the way how `pyRAP` will align them within a cell. For non-terminal widgets like the :class:`Composite`,
an additional parameter must be considered in case ``valign`` or ``halign`` are set to ``'fill'``. In this case,
it is required to specify how the remaining free space of the grid cell will be distributed among the columns
or rows their children reside in. The layout parameters to do so are called ``flexrows`` and ``flexcols``. They determine the
rows or columns, which are assigned a "flexible" width or height, respectively. ``flexrows`` and ``flexcols``
may be either dictionaries mapping column/row indices to a positive real-valued weight specifying the proportions
of the free space of the grid cell the respective column/row will be assigned. For example, ::

    Composite(parent, layout=Gridlayout(halign='fill', flexcols={1: .66, 2: .33}))

creates a composite with a grid layout, whose remaining horizontal grid cell space will be distributed
among the second (index 1) and third (index 2) column with proportions 2:1.

.. note::
   The weights of ``flexcols`` and ``flexrows`` are not required to sum to one as `pyRAP` automatically
   normalizes the weights when computing the layout. Therefore, ``flexcols={1: 2.0, 2: 1.0}`` is equivalent
   to the above example.

There are also two shortcuts for the
parameters ``flexrows`` and ``flexcols``: When they are passed in the form of a list, their list elements are interpreted
as column/row indices with weight ``1``, i.e. the free space will be distributed evenly among those columns/rows.
When they are passed as a single integer, the column/row with that particular index will be
stretched to the entire remaining space. If the remaining space of a grid cell is supposed to be distributed
over `all` columns/rows of a grid layout, ``equalwidths=True`` or ``equalheights=True`` may be specified instead
of explicitly enumerating all flexcols/flexrow indices. For illustrating the use and effects of flexible rows
and columns, consider the following ``stretch`` entry point, which is also part of the ``GridLayoutExample`` `pyRAP`
app:

.. code-block:: python
   :linenos:

    def stretch(self, **kwargs):
        equalwidths = {'true': True, 'false': False}[kwargs.get('equalwidths', 'false').lower()]
        flexcols = None
        equalheights = {'true': True, 'false': False}[kwargs.get('equalheights', 'false').lower()]
        flexrows = None
        if not equalwidths:
            flexcols = 0
        if not equalheights:
            flexrows = 0
        shell = Shell(title='GridLayout with flexible rows and columns', maximized=True)
        shell.content.layout = GridLayout(rows=5, halign='fill', valign='fill', equalwidths=equalwidths, equalheights=equalheights, flexcols=flexcols, flexrows=flexrows)
        for i in range(20):
            Button(shell.content, text='Button %.2d' % (i+1), halign='fill', valign='fill')
        shell.on_resize += shell.dolayout
        shell.show(True)

The app creates a Shell window that is maximized, so it will fill out the whole body area of the client browser.
Its ``content`` composite layout is specified as a :class:`GridLayout` that will be vertically and horizontally
filled to the shell. Therefore, we have to specify how the excess space within the window shall be distributed.
To this end, the app accepts the two optional boolean arguments ``equalwidths`` and ``equalheights``, which are
passed to the grid layout. If they are ``False`` (which is the case by default), we specify that the respective first
row or column shall receive all the excess space (cf. line 7 and 9). The different parameterizations and their
URL calls are shown below:

.. container:: twocol

   .. container:: left

      .. figure:: _static/gridlayout-stretch.png
         :height: 300pt

         ``http://localhost:8080/grid/stretch``

   .. container:: right

      .. figure:: _static/gridlayout-stretch-ew.png
         :height: 300pt

         ``http://localhost:8080/grid/stretch?equalwidths=true``

.. container:: twocol

   .. container:: left

      .. figure:: _static/gridlayout-stretch-eh.png
         :height: 300pt

         ``http://localhost:8080/grid/stretch?equalheights=true``

   .. container:: right

      .. figure:: _static/gridlayout-stretch-ew-eh.png
         :height: 300pt

         ``http://localhost:8080/grid/stretch?equalheights=true&equalwidths=true``

Feel free to modify the ``stretch`` example: For instance, replace line 7 and 9 by ::

    flexcols = {0: 2, 2:1}

and ::

    flexrows = {1: 1, 2: 2, 3: 3, 4:4}


ColumnLayout
------------

RowLayout
---------

CellLayout
----------

StackLayout
-----------
