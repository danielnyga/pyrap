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

    var that = this;
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
    this.setBounds( parent.getClientArea() );
};

pwt.SVG.prototype = {

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        parent.append( element );
        return element;
    },

    getcontainer: function() {
        return this.svg;
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    setSvg : function( svgcontent ) {
        this._parentDIV.innerHTML = svgcontent;
        this.svg = this._parentDIV.childNodes[0];
    },

    setAttr : function( attr ) {
        el = document.getElementById(attr[0]);
        el.setAttribute(attr[1], attr[2]);
    },

    highlight : function ( args ) {
        if (document.getElementById(args.id)) {
            document.getElementById(args.id).style.fill = args.clear ? "none" : "#bee280";
        }
    },

    clear : function ( args ) {
        for (var i = 0; i < args.ids.length; i++) {
            if (document.getElementById(args.ids[i])) {
                document.getElementById(args.ids[i]).style.fill = "none";
            }
        }
    },

     setBounds: function( args ) {
        console.log('setting bounds to ', args);
        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
        console.log('after setting bounds', this._parentDIV);
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
    console.log('svg parent', parent);
    return new pwt.SVG( parent, properties.cssid, properties.svg );
  },

  destructor: 'destroy',

  properties: [ 'remove', 'attr', 'svg', 'bounds'],

  methods : [ "clear", "highlight" ],

  events: [ ]

} );