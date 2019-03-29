pwt_scatterplot = {};

pwt_scatterplot.Scatterplot = function( parent, options ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'scattertooltip')
        .style('z-index', 1000000);

    this._cfg = {
        margin: { top: 50, right: 50, bottom: 50, left: 50 },
        formatDefault: d3.format(',.2f'),
        color: d3.scale.category20()
	};

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.scatter');

    this._w = 800;
    this._h = 600;

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

pwt_scatterplot.Scatterplot.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'scatter')
                .attr("transform", "translate("  + this._cfg.margin.left + ',' + this._cfg.margin.top + ")");
            this._svgContainer = this._svg.select('g.scatter');
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
        this._w = args[2] ? args[2] - this._cfg.margin.left - this._cfg.margin.right : 800;
        this._h = args[3] ? args[3] - this._cfg.margin.top - this._cfg.margin.bottom : 600;
        this.update();
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    destroy: function() {
        var element = this._parentDIV;
        if ( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setWidth: function( width ) {
        this._parentDIV.style.width = width + "px";
        this._w = width - this._cfg.margin.left - this._cfg.margin.right;
        this.update();
    },

    setHeight: function( height ) {
        this._parentDIV.style.height = height + "px";
        this._h = height - this._cfg.margin.top - this._cfg.margin.bottom;
        this.update();
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        this._data = data;
        this.update();
    },

    /**
     * updates axes labels
     */
    axes : function ( data ) {
        this._xlabel = data.labels ? data.labels[0] : '';
        this._ylabel = data.labels ? data.labels[1] : '';
        this.update();
    },

    /**
     * updates the formatter for the x/y axes ticks
     */
    formats : function ( data ) {
        this._xformat = function(d) {
            return data.xformat.prefix + d3.format(data.xformat.format)(d) + data.xformat.postfix;
        };
        this._yformat = function(d) {
            return data.yformat.prefix + d3.format(data.yformat.format)(d) + data.yformat.postfix;
        };
        this.update();
    },

    /**
     * clear plot by emptying data
     */
    clear : function() {
        this.setData( {} );
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( data ) {
        var attrs = this._svg.node().attributes;

        // saving old attributes
        var orig = {};
        for (var i=0; i<attrs.length; i++)
            orig[attrs[i].name] = attrs[i].value;

        // updating attributes for export
        this._svg
            .attr('width', data.width + 'px')
            .attr('height', data.height + 'px')
            .attr('viewBox', [0, 0, data.width, data.height].join(' '));

        // adding css styles
        if (data.defs) {
            if (!this._defs) {
                this._defs = this._svgContainer.append("defs");
            }
            this._defs.html(this._defs.node().innerHTML + data.defs);

        }
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( 'svg', this._svg.node().outerHTML );

        // removing set attributes
        this._svg
            .attr('width', null)
            .attr('height', null)
            .attr('viewBox', null);

        // restoring original attributes
        for (var key in orig) {
            this._svg
                .attr(key, orig[key]);
        }
    },

    /**
     * redraws the plot with the updated data
     */
    update : function () {

        if (!this._initialized) { return; }

        var that = this;

        var xScale = d3.scale.linear()
            .domain([
                d3.min([0, d3.min(this._data, function (d) { return d.x })]),
                d3.max([0, d3.max(this._data, function (d) { return d.x })])
            ])
            .range([0, this._w]);

        var yScale = d3.scale.linear()
            .domain([
                d3.min([0, d3.min(this._data, function (d) { return d.y })]),
                d3.max([0, d3.max(this._data, function (d) { return d.y })])
            ])
            .range([this._h, 0]);

        // X-axis
        var xAxis = d3.svg.axis()
            .scale(xScale)
            .tickFormat(this._xformat)
            .ticks(5)
            .orient('bottom');

        // Y-axis
        var yAxis = d3.svg.axis()
            .scale(yScale)
            .tickFormat(this._yformat)
            .ticks(5)
            .orient('left');

        // Circles
        var circles = this._svgContainer.selectAll('circle.scattercircle').data(this._data);

        // circle creation
        circles
            .enter()
            .append('circle')
            .attr('class','scattercircle')
            .attr('fill',function (d,i) { return that._cfg.color(i) })
            .on('mouseover', function () {
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.tooltip)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on('mouseout', function () {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        // circle update
        circles
            .attr('cx',function (d) { return xScale(d.x) })
            .attr('cy',function (d) { return yScale(d.y) })
            .attr('r', 10);

        circles.exit().remove();

        // X-axis
        var xaxis = this._svgContainer.selectAll("g.axis.xaxis").data([0]);
        var xaxislabel = xaxis.selectAll(".label");

        // create axis group
        var xaxisenter = xaxis
            .enter()
            .append("g")
                .attr("class", "axis xaxis")
                .attr('transform', 'translate(0,' + this._h + ')');

        xaxis.call(xAxis);

        xaxisenter
            .append('text') // X-axis Label
                .attr('class','label')
                .attr('y', -12)
                .attr('x', this._w)
                .attr('dy','.71em')
                .style('text-anchor','end')
                .text(this._xlabel);

        xaxis
            .attr('transform', 'translate(0,' + this._h + ')');

        xaxislabel
            .attr('x', this._w);

        xaxis.exit().remove();

        // Y-axis
        var yaxis = this._svgContainer.selectAll("g.axis.yaxis").data([0]);

        // create axis group
        var yaxisenter = yaxis
            .enter()
            .append("g")
                .attr("class", "axis yaxis");

        yaxis.call(yAxis);

        yaxisenter
            .append('text') // Y-axis Label
                .attr('class','label')
                .attr('transform','rotate(-90)')
                .attr('y', 5)
                .attr('x', 0)
                .attr('dy','.71em')
                .style('text-anchor','end')
                .text(this._ylabel);

        yaxis.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Scatterplot', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_scatterplot.Scatterplot( parent, properties);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'axes', 'formats', 'retrievesvg'],
    events: [ 'Selection' ]

} );