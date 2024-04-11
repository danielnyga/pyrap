pwt_plotly = {};

pwt_plotly.Plotly = function( parent, opts ) {
    this._parentDIV = this.createElement(parent);
    this._tooltip = d3v3.select(this._parentDIV).append("div")
        .attr('class', 'plotlytooltip')
        .style('z-index', 1000000);

    this._cfg = {
        url: opts.url,
        plotid: this.makeId(opts.id)
    };

    this._id = null;
    this._plotlyplot = null;

    this._initialized = false;
    this._needsRender = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( !that._initialized) {
                that.initialize( that );
                that._initialized = true;
            }
            that.update();
            that._needsRender = false;
        }
    } );
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
};

pwt_plotly.Plotly.prototype = {


    initialize: function() {
        this._id = rwt.remote.Connection.getInstance().getRemoteObject( this )._.id;
        this._plotlyplot = d3v3.select(this._parentDIV).append("iframe")
            .attr("id", "plotly_" + this._id)
            .attr("src", this._cfg.url)
            .style("width", "1000px")
            .style("height", "800px");
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

    setBounds: function( args ) {
        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
        this.update();
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    destroy: function() {
        var element = this._parentDIV;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setWidth: function( width ) {
        this._parentDIV.style.width = width + "px";
        this._w = width;
        this.update();
    },

    setHeight: function( height ) {
        this.this._parentDIV.style.height = height + "px";
        this._h = height;
        this.update();
    },

    /**
     * removes all axes from the radar chart
     */
    clear : function ( ) {
        this.setData( {} );
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, [this._svg.node().outerHTML, args.fname] );
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        // preprocess data
        this._data = data;
        this.update();
    },

    setUrl: function( url ) {
        this._cfg.url = url;
        this.update();
    },

    makeId: function ( plotid ) {
        this._plotid = plotid;
        this.update();
    },

    /**
     * redraws the pot with the updated url
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        // only re-render plot if url changed
        if ( this._cfg.url !== that._plotlyplot[0].at(0).src ) {
            that._plotlyplot[0].at(0).src = this._cfg.url;
        }

    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Plotly', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_plotly.Plotly( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds', 'url'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );