pwt_barchart = {};

pwt_barchart.BarChart = function( parent, options ) {

    this.barHeight = 15;
    this.topOffset = 20;
    this.fontpixels = 10; //x-small
    this.yBarWidth = 0;
    this.barChartData = [];

    this._parentDIV = this.createElement(parent);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.barchart');

    this._tooltip = d3.select(this._parentDIV).append("div")
            .attr('class', 'barcharttooltip')
            .style('z-index', 1000000);

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

pwt_barchart.BarChart.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'barchart')
                .attr("transform", "translate(" + this.yBarWidth + "," + this.topOffset + ")");
            this._svgContainer = this._svg.select('g.barchart');
        }

        this._svgContainer.append("g")
            .attr("class", "x bcaxis");

        this._svgContainer.append("g")
            .attr("class", "y bcaxis");
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
        this._w = args[2];
        this._h = args[3];
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

    /**
     * updates data set for bar chart
     */
    setData : function (results) {
        this.clear();
        this.barChartData = results.slice();
        this.barChartData.sort(function(a, b) { return a.value - b.value; });

        // determine horizontal translation based on the maximum string length of the y axis items
        var l = [];
        for (var e = 0; e < this.barChartData.length; e++) {
            l.push(this.barChartData[e].name);
        }
        if (l.length > 0) {
            this.yBarWidth = l.reduce(function (a, b) { return a.length > b.length ? a : b; }).length * this.fontpixels;
        }

        this.update();
    },

    /**
     * clear bar chart by emptying data
     */
    clear : function() {
      this.barChartData.splice(0, this.barChartData.length);
      this.update();
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, this._svg.node().outerHTML );
    },

    Format : function(x) {
        return d3.format(".2%")(x);
    },

    /**
     * redraws the bar chart with the updated data
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { rap._.notify('render'); }

        var that = this;

        this._svgContainer
            .attr("transform", "translate(" + this.yBarWidth + "," + this.topOffset + ")");

        this.xscale = d3.scale.linear()
            .range([0, this._w - this.yBarWidth - 5*this.fontpixels])
            .domain([0, 1]);

        this.yscale = d3.scale.ordinal()
            .rangeRoundBands([this.barChartData.length * 1.2 * this.barHeight, 0])
            .domain(this.barChartData.map(function(d) { return d.name; }));

        var xAxis = d3.svg.axis()
            .scale(this.xscale)
            .orient("top")
            .innerTickSize(5)
            .outerTickSize(1);

        var yAxis = d3.svg.axis()
            .scale(this.yscale)
            .orient("left")
            .innerTickSize(5)
            .outerTickSize(1);

        // selection for bars
        var bars = this._svgContainer.selectAll("g.bar").data(this.barChartData, function(d) { return d.name; });

        // create elements (bars)
        var barsenter = bars
            .enter()
            .append("g")
            .attr("class", "bar")
            .attr("transform", function(d) { return "translate(0," + that.yscale(d.name) + ")"; });

        // create bars
        barsenter.append("rect")
            .attr("width", function(d) { return that.xscale(d.value); })
            .attr("height", this.barHeight)
            .on("mouseover", function(d) {
                that._tooltip
                    .transition(200)
                    .style('display', 'block');
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(that.Format(d.value))
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        // update bars
        bars.select('rect')
            .attr("width", function(d) { return that.xscale(d.value); });

        // create texts
        barsenter.append("text")
            .attr("class", "value")
            .attr("x", function(d) { return that.xscale(d.value); })
            .attr("y", that.yscale.rangeBand() / 2)
            .attr("dx", function(d) { return d.value > .1 ? -3 : "4em"; })
            .attr("dy", ".35em")
            .attr("text-anchor", "end")
            .text(function(d) { return that.Format(d.value); });

        bars.select('text')
            .attr("x", function(d) { return that.xscale(d.value); })
            .attr("y", that.yscale.rangeBand() / 2)
            .attr("dx", function(d) { return d.value > .1 ? -3 : "4em"; });

        // remove elements
        bars.exit().remove();

        this._svg.selectAll("g.y.bcaxis")
            .call(yAxis);

        this._svg.selectAll("g.x.bcaxis")
            .call(xAxis);
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.BarChart', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_barchart.BarChart( parent, properties);
    },

    destructor: 'destroy',
    properties: [ 'bounds', 'data'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );