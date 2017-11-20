import os

from pyrap import locations
from pyrap import session
from pyrap.communication import RWTSetOperation
from pyrap.dialogs import options_list
from pyrap.events import OnSelect, OnModify
from pyrap.layout import ColumnLayout
from pyrap.ptypes import BitField, px, Image
from pyrap.themes import CompositeTheme
from pyrap.widgets import Composite, Widget, checkwidget, Edit, Label, constructor, \
    Button


class ComboMobile(Composite):
    _rwt_class_name_ = 'rwt.widgets.Composite'
    _defstyle_ = BitField(Widget._defstyle_)

    @constructor('ComboMobile')
    def __init__(self, parent, items=None, editable=True, message=None, text=None, **options):
        Widget.__init__(self, parent, **options)
        if items is None:
            items = []
        self.theme = CompositeTheme(self, session.runtime.mngr.theme)
        self.layout = ColumnLayout(flexcols=0, halign='fill', valign='fill')
        self._items = items
        self._message = message
        self._text = text
        self.on_select = OnSelect(self)
        self.on_modify = OnModify(self)
        self._editable = editable
        self._selection = None

    def create_content(self):
        self._edit = Edit(self, text=self._text, message=self._message, editable=self._editable, valign='fill', halign='fill')
        self._edit.layout.padding_right = px(0)
        self._btn = Button(self, img=Image(os.path.join(locations.rc_loc, 'theme', 'img', 'combo', 'down.png')), halign='fill', valign='fill')
        self._btn.layout.padding_left = px(0)
        self._btn.on_select += self._selectinstruction

    @Widget.bounds.setter
    @checkwidget
    def bounds(self, bounds):
        if not len(bounds) == 4: raise Exception('Illegal bounds: %s' % str(bounds))
        self._bounds = list(map(px, bounds))
        session.runtime << RWTSetOperation(self.id, { 'bounds': [b.value for b in self.bounds]})
        session.runtime << RWTSetOperation(self.id, { 'clientArea': [0, 0, self.bounds[2].value, self.bounds[3].value]})


    def _selectinstruction(self, *_):
        key, value = options_list(self.shell(), self._items)
        self._edit.text = key
        self._selection = value

    def compute_size(self):
        return Widget.compute_size(self)

    @property
    def text(self):
        return self._edit.text

    @text.setter
    @checkwidget
    def text(self, text):
        self._edit.text = text
        self._text = text
        self._selection = None
        session.runtime << RWTSetOperation(self._edit.id, {'text': self.text})

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, items):
        self._items = items

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, sel):
        self.text = sel