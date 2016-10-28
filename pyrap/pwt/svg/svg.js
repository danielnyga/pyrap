pwt = {};
svgNS = "http://www.w3.org/2000/svg";

pwt.SVG = function(parent, cssid, svg) {
    console.log('initialize!');

    this._parent = this.createElement(parent);
    if (cssid) {
        this._parent.setAttribute('id', cssid);
    }
    if (svg) {
        this._parent.innerHTML = svg;
        this.svg = this._parent.childNodes[0];
    } else {
        this.svg = document.createElementNS(svgNS, "svg");
        this.svg.setAttributeNS("http://www.w3.org/2000/xmlns/", "xmlns:xlink", "http://www.w3.org/1999/xlink");
        this.svg.setAttribute('encoding', 'utf-8');
        this._parent.append( this.svg );
    }

    this._needsLayout = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( that._needsLayout ) {
                that.initialize( that );
                that._needsLayout = false;
            }
            that.render( that );
            that._needsRender = false;
        }
    } );
    parent.addListener( "Resize", function() {
        that._resize( parent.getClientArea() );
    } );
    this._resize( parent.getClientArea() );
};

pwt.SVG.prototype = {

    initialize: function() {
        console.log('initialize!');
    },

    render: function() {
        console.log('render!');
    },

    createElement: function( parent ) {
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = "0";
        element.style.top = "0";
        element.style.width = "100%";
        element.style.height = "100%";
        parent.append( element );
        return element;
    },

    getcontainer: function() {
        return this.svg;
    },

    setZIndex : function(e) {
//        this._parent.setZIndex(e);
        console.log('someone tried to set my zindex!', e);
    },

    setSvg : function( svgcontent ) {
        console.log('setting svgcontent');
        this._parent.innerHTML = svgcontent;
        this.svg = this._parent.childNodes[0];
    },

    setAttr : function( attr ) {
        console.log(attr);
        el = document.getElementById(attr[0]);
        el.setAttribute(attr[1], attr[2]);
    },

    setIdstyle : function ( style ) {
        console.log('style', style);
        if (style[0]) {
            document.getElementById(style[0]).style.fill = style[3] ? "none" : "#bee280";
        }
    },

    _resize: function( clientArea ) {
        this._width = clientArea[ 2 ];
        this._height = clientArea[ 3 ];
        this._scheduleUpdate( false );
    },

    _scheduleUpdate: function( needsLayout ) {
        if( needsLayout ) {
            this._needsLayout = true;
        }
        this._needsRender = true;
    },

    addelem : function() {
        console.log('addelem!');
    },

    destroy: function() {
        var element = this._parent;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
  }

};

// Type handler
rap.registerTypeHandler( 'pwt.customs.SVG', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    console.log('svg parent', parent);
    return new pwt.SVG( parent, properties.cssid, properties.svg );
  },

  destructor: 'destroy',

  properties: [ 'remove', 'attr', 'idstyle', 'svg'],

  events: [ ]

} );