d3graph = {};

d3graph.Graph = function(parent, cssid, cssclass, renderer) {
    this._renderer = renderer;

    this._parent = this.createElement(parent);

    this._svg = d3.select(this._parent)
        .append("svg");

    if (cssid) {
        d3.select(this._parent).select('svg')
            .attr( "id", cssid );
    }
    if (cssclass) {
        d3.select(this._parent).select('svg')
            .attr( "class", cssclass );
    }

    this._needsLayout = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( that._needsLayout ) {
                that._renderer.initialize( that );
                that._needsLayout = false;
            }
            that._renderer.render( that );
            that._needsRender = false;
        }
    } );
    parent.addListener( "Resize", function() {
        that._resize( parent.getClientArea() );
    } );
    this._resize( parent.getClientArea() );
};

d3graph.Graph.prototype = {

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
        return this._svg;
    },


    _resize: function( clientArea ) {
        this._width = clientArea[ 2 ];
        this._height = clientArea[ 3 ];
        this._svg.attr( "width", this._width ).attr( "height", this._height );
        this._scheduleUpdate( false );
    },

    _scheduleUpdate: function( needsLayout ) {
        if( needsLayout ) {
            this._needsLayout = true;
        }
        this._needsRender = true;
    },

    destroy: function() {
        var element = this._parent;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Graph', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new d3graph.Graph( parent, properties.cssid, properties.cssclass);
  },

  destructor: 'destroy',

  properties: [ 'remove' ],

  events: [ ]

} );