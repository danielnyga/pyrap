pwt_template = {};

pwt_template.Template = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'templatetooltip')
        .style('z-index', 1000000);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.template');

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

pwt_template.Template.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'template')
                .attr("transform", "translate(" + (this._wwidth/2) + "," + (this._wheight/2) + ")");
            this._svgContainer = this._svg.select('g.template');
        }
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


    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }
        if (!this._dataloaded) { return; }

        var that = this;

        // put d3js code here
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Template', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_template.Template( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );