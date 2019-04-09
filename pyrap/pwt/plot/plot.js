pwt_scatterplot = {};

pwt_scatterplot.Scatterplot = function( parent, options ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'scattertooltip')
        .style('z-index', 1000000);

    this._cfg = {
        margin: { top: 50, right: 50, bottom: 50, left: 50 },
        formatDefault: d3.format(',.2f'),
        scattercolor: d3.scale.ordinal()
            .range(['#e41a1c','#0a4db8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999',
                '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd',
                '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
                '#17becf', '#9edae5']),
        linecolor: d3.scale.ordinal()
            .range(['#e41a1c','#0a4db8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999',
                '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd',
                '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
                '#17becf', '#9edae5'])
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
        this._scatterdata = data.scatter ? data.scatter : [];
        this._linedata = data.line ? data.line : {};
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
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, this._svg.node().outerHTML );
    },

    /**
     * determines the min and max values for the x/y-axes from the line data
     */
    linelimits : function() {
        var lx = Number.POSITIVE_INFINITY;
        var ly = Number.POSITIVE_INFINITY;
        var ux = Number.NEGATIVE_INFINITY;
        var uy = Number.NEGATIVE_INFINITY;
        var tmpx, tmpy;

        for (var key in this._linedata){

            for (var i=0; i<this._linedata[key].length; i++) {
                tmpx = this._linedata[key][i].x;
                tmpy = this._linedata[key][i].y;
                lx = tmpx < lx ? tmpx : lx;
                ux = tmpx > ux ? tmpx : ux;
                ly = tmpy < ly ? tmpy : ly;
                uy = tmpy > uy ? tmpy : uy;
            }
        }
        return {'x': [lx, ux], 'y': [ly, uy]};
    },

    /**
     * determines the min and max values for the x/y-axes from the scatter data
     */
    scatterlimits : function() {
        return {'x': [d3.min([0, d3.min(this._scatterdata, function (d) { return d.x })]),
                      d3.max([0, d3.max(this._scatterdata, function (d) { return d.x })])],
                'y': [d3.min([0, d3.min(this._scatterdata, function (d) { return d.y })]),
                      d3.max([0, d3.max(this._scatterdata, function (d) { return d.y })])]};
    },

    /**
     * redraws the plot with the updated data
     */
    update : function () {

        if (!this._initialized) { return; }

        var that = this;

        this._cfg.scattercolor
            .domain([Array(this._scatterdata.length).keys()]);

        // generate limits for x/y axes from data; prefer scatterdata over line data
        var limits = typeof this._scatterdata !== 'undefined' && this._scatterdata.length > 0 ? this.scatterlimits() : this.linelimits();
        var xScale = d3.scale.linear()
            .domain([limits.x[0], limits.x[1]])
            .range([0, this._w]);

        var yScale = d3.scale.linear()
            .domain([limits.y[0], limits.y[1]])
            .range([this._h, 0]);

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE NODES                               ///
        ////////////////////////////////////////////////////////////////////////

        // circle groups selection
        var circlegroups = this._svgContainer.selectAll('g.scatternode').data(this._scatterdata);

        // circle groups creation
        var circlegroupsenter = circlegroups
            .enter()
            .append('g')
            .attr("class", "scatternode")
            .attr("transform", function(d){return "translate("+xScale(d.x) + "," + yScale(d.y) + ")"});

        // circle groups update
        circlegroups
            .attr("transform", function(d){return "translate("+xScale(d.x) + "," + yScale(d.y) + ")"});

        // circle creation
        circlegroupsenter
            .append("circle")
            .attr("class", "scattercircle")
            .attr('fill',function (d,i) { return that._cfg.scattercolor(i) })
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

        // update nodes
        circlegroups.select('.scattercircle')
            .attr('r', 10);

        // circle text creation
        circlegroupsenter
            .append("text")
            .attr("class", "scattertext")
            .attr("dx", function(d){return 0;})
            .attr("dy", function(d){return 10;})
            .text(function(d){return d.tooltip});

        // circle text update
        circlegroups.select('.scattertext')
            .text(function(d){return d.name});

        // circlegroups removal
        circlegroups.exit().remove();


        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LINES                               ///
        ////////////////////////////////////////////////////////////////////////

        this._cfg.linecolor
            .domain(Object.keys(this._linedata));

        var valueline = function (d) {
            return d3.svg.line()
                     .x(function(d) { return xScale(d.x); })
                     .y(function(d) { return yScale(d.y); })
                     (d)
        };

        Object.keys(this._linedata).forEach(function(key, idx) {
            // line groups selection
            var linegroups = that._svgContainer.selectAll("g.pathnode" + "-" + key).data([0]);

            // line groups creation
            var linegroupsenter = linegroups
                .enter()
                .append('g')
                .attr("class", "pathnode" + "-" + key);

            // lines creation
            linegroupsenter
                .append("path")
                .attr("stroke", function(d){ return that._cfg.linecolor(key); })
                .attr("class", "scatterline")
                .attr("d", function(d){ return valueline(that._linedata[key]);})
                .on('mouseover', function () {
                    that._tooltip
                        .transition(200)
                        .style("display", "block");
                })
                .on('mousemove', function(d) {
                    var newX = (d3.event.pageX + 20);
                    var newY = (d3.event.pageY - 20);
                    that._tooltip
                        .html(key)
                        .style("left", (newX) + "px")
                        .style("top", (newY) + "px");
                })
                .on('mouseout', function () {
                    that._tooltip
                        .transition(200)
                        .style("display", "none");
                });

            // lines update
            linegroups.select('.scatterline')
                .attr("d", function(d){ return valueline(that._linedata[key]);});

            // linegroups removal
            linegroups.exit().remove();
        });

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE AXES                                ///
        ////////////////////////////////////////////////////////////////////////

        // X-axis ticks
        var xAxis = d3.svg.axis()
            .scale(xScale)
            .tickFormat(this._xformat)
            .ticks(5)
            .orient('bottom');

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

        // Y-axis ticks
        var yAxis = d3.svg.axis()
            .scale(yScale)
            .tickFormat(this._yformat)
            .ticks(5)
            .orient('left');

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