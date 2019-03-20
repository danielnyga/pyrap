pwt = {};
svgNS = 'http://www.w3.org/2000/svg';

pwt.SVG = function(parent, cssid, svg) {

    this._parentDIV = this.createElement(parent);

    if (svg) {
        this._parentDIV.innerHTML = svg;
        this.svg = this._parentDIV.childNodes[this._parentDIV.childNodes.length-1];
    } else {
        this.svg = document.createElementNS(svgNS, 'svg');
        this.svg.setAttributeNS('http://www.w3.org/2000/xmlns/', 'xmlns:xlink', 'http://www.w3.org/1999/xlink');
        this.svg.setAttribute('encoding', 'utf-8');

        this._parentDIV.append( this.svg );
    }
    this.svg.setAttribute('width', "100%");
    this.svg.setAttribute('height', "100%");

    if (cssid) {
        this.svg.setAttribute('id', cssid);
    }

    var that = this;
    parent.addListener( 'Resize', function() {
        that.setBounds( parent.getClientArea() );
    } );
    this.setBounds( parent.getClientArea() );
};

pwt.SVG.prototype = {

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( 'div' );
        element.style.position = 'absolute';
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
        this.svg = this._parentDIV.childNodes[this._parentDIV.childNodes.length-1];
        this.svg.setAttribute('width', "100%");
        this.svg.setAttribute('height', "100%");
    },

    elAttribute : function( args ) {
        if (this.svg.getElementById(args.id)) {
            this.svg.getElementById(args.id).setAttribute(args.attribute, args.value);
        }
    },

    attribute : function( args ) {
        this.svg.setAttribute(args.attribute, args.value);
    },

    highlight : function ( args ) {
        if (document.getElementById(args.id)) {
            document.getElementById(args.id).style.fill = args.clear ? '#ffffff' : '#bee280';
            document.getElementById(args.id).style.fillOpacity = args.clear ? '0.05' : '1';
        }
    },

    clear : function ( args ) {
        for (var i = 0; i < args.ids.length; i++) {
            if (document.getElementById(args.ids[i])) {
                document.getElementById(args.ids[i]).style.fill = '#ffffff';
                document.getElementById(args.ids[i]).style.fillOpacity = '0.05';
            }
        }
    },

     setBounds: function( args ) {
        this._parentDIV.style.left = args[0] + 'px';
        this._parentDIV.style.top = args[1] + 'px';
        this._parentDIV.style.width = args[2] + 'px';
        this._parentDIV.style.height = args[3] + 'px';
     },

    destroy: function() {
        var element = this._parentDIV;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setSelectelem: function( elems ) {
        for (var x = 0; x < elems.length; x++) {
            var el = document.getElementById(elems[x]);

            var that = this;
            var sel = function(event) {
                rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'mousedown': event.target.id } );
            };

            el.addEventListener("touchstart", sel, true);
            el.addEventListener("mousedown",  sel, true);
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

  properties: [ 'remove', 'svg', 'bounds', 'selectelem'],

  methods : [ 'clear', 'highlight', 'attribute', 'elAttribute'],

  events: [ 'Selection' ]

} );