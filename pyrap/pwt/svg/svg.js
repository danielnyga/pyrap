pwt = {};
svgNS = "http://www.w3.org/2000/svg";

pwt.SVG = function(parent, cssid, svg) {
    this._parentDIV = this.createElement(parent);
    if (cssid) {
        this._parentDIV.setAttribute('id', cssid);
    }
    if (svg) {
        this._parentDIV.innerHTML = svg;
        this.svg = this._parentDIV.childNodes[0];
    } else {
        this.svg = document.createElementNS(svgNS, "svg");
        this.svg.setAttributeNS("http://www.w3.org/2000/xmlns/", "xmlns:xlink", "http://www.w3.org/1999/xlink");
        this.svg.setAttribute('encoding', 'utf-8');
        this._parentDIV.append( this.svg );
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
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = clientarea[2] + "px";
        element.style.height = clientarea[3] + "px";
        console.log('clientarea', clientarea);
        console.log('parent', parent);
        console.log('element', element);
        parent.append( element );
        return element;
    },

    getcontainer: function() {
        return this.svg;
    },

    setZIndex : function(e) {
        console.log('someone tried to set my zindex!', e);
    },

    setSvg : function( svgcontent ) {
        console.log('setting svgcontent');
        this._parentDIV.innerHTML = svgcontent;
        this.svg = this._parentDIV.childNodes[0];
    },

    setAttr : function( attr ) {
        console.log('setattr', attr);
        el = document.getElementById(attr[0]);
        el.setAttribute(attr[1], attr[2]);
    },

    highlight : function ( args ) {
        if (document.getElementById(args.id)) {
            document.getElementById(args.id).style.fill = args.clear ? "#ffffff" : "#bee280";
        }
    },

    clear : function ( args ) {
        for (var i = 0; i < args.ids.length; i++) {
            if (document.getElementById(args.ids[i])) {
                document.getElementById(args.ids[i]).style.fill = "none";
            }
        }
    },

    _resize: function( clientArea ) {
        console.log('this', this);
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
        var element = this._parentDIV;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
  }

};

// Type handler
rap.registerTypeHandler( 'pwt.customs.SVG', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt.SVG( parent, properties.cssid, properties.svg );
  },

  destructor: 'destroy',

  properties: [ 'remove', 'attr', 'svg'],

  methods : [ "clear", "highlight" ],

  events: [ ]

} );