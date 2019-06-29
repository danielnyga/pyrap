pwt_SVG = {};
svgNS = 'http://www.w3.org/2000/svg';

pwt_SVG.SVG = function(parent, cssid, svg) {

    this._parentDIV = this.createElement(parent);

    if (svg) {
        this._parentDIV.innerHTML = svg;
        this._svg = this._parentDIV.childNodes[this._parentDIV.childNodes.length-1];
    } else {
        this._svg = document.createElementNS(svgNS, 'svg');
        this._svg.setAttributeNS('http://www.w3.org/2000/xmlns/', 'xmlns:xlink', 'http://www.w3.org/1999/xlink');
        this._svg.setAttribute('encoding', 'utf-8');

        this._parentDIV.append( this._svg );
    }

    if (cssid) {
        this._svg.setAttribute('id', cssid);
    }

    this._initialized = false;
    this._needsRender = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( !that._initialized) {
                that.initialize( that );
                that._initialized = true;
            }
            that._needsRender = false;
        }
    } );
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
};

pwt_SVG.SVG.prototype = {

    initialize: function() {

        this._svg.setAttribute('width', "100%");
        this._svg.setAttribute('height', "100%");
    },

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = clientarea[2];
        element.style.height = clientarea[3];
        parent.append( element );
        return element;
    },

    getcontainer: function() {
        return this._svg;
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    setSvg : function( svgcontent ) {
        this._parentDIV.innerHTML = svgcontent;
        this._svg = this._parentDIV.childNodes[this._parentDIV.childNodes.length-1];
        this._svg.setAttribute('width', "100%");
        this._svg.setAttribute('height', "100%");
    },

    elAttribute : function( args ) {
        if (this._svg.getElementById(args.id)) {
            this._svg.getElementById(args.id).setAttribute(args.attribute, args.value);
        }
    },

    attribute : function( args ) {
        this._svg.setAttribute(args.attribute, args.value);
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
        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
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
    return new pwt_SVG.SVG( parent, properties.cssid, properties.svg );
  },

  destructor: 'destroy',

  properties: [ 'remove', 'svg', 'bounds', 'selectelem'],

  methods : [ 'clear', 'highlight', 'attribute', 'elAttribute'],

  events: [ 'Selection' ]

} );