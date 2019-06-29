import io
import os
import tempfile

from pyrap import session
from pyrap.ptypes import SVG

from svglib.svglib import svg2rlg
from reportlab.graphics import renderPDF


def downloadsvg(cnt, w, h, css, name='tmpviz'):
    svg = SVG()
    svg.load(cnt, w=w, h=h, css=css)

    stream = io.BytesIO()
    svg.save(stream)
    session.runtime.download('{}.svg'.format(name), 'image/svg+xml', stream.getvalue(), force=True)
    stream.close()


def downloadpdf(cnt, w, h, css, name='tmpviz'):
    tmpfile = os.path.join(tempfile.gettempdir(), 'viz.svg')
    svg = SVG()
    svg.load(cnt, w=w, h=h, css=css)

    with open(tmpfile, 'wb') as f:
        svg.save(f)

    svgcontent = svg2rlg(tmpfile)
    v = renderPDF.drawToString(svgcontent)
    session.runtime.download('{}.pdf'.format(name), 'application/pdf', v, force=True)
    os.remove(tmpfile)

