pwt_barchart = {};

pwt_barchart.BarChart = function( parent, options ) {

    this.barHeight = 15;
    this.topOffset = 20;
    this.w = 0;
    this.h = 0;
    this.fontpixels = 7.5; //x-small
    this.yBarWidth = 0;
    this.barChartData = [];

    this._parentDIV = this.createElement(parent);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.barchart');

    var that = this;
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

        this.w = this._parentDIV.offsetWidth;
        this.h = 1;//this._parentDIV.offsetHeight;

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
            .attr("class", "x axis");

        this._svgContainer.append("g")
            .attr("class", "y axis");
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
        this.barChartData.sort(function(a, b) { return b.value - a.value; });
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
     * redraws the bar chart with the updated data
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        this.w = this._parentDIV.offsetWidth;
        this.h = this.barChartData.length * 1.2 * this.barHeight;

        this._svgContainer
            .attr("transform", "translate(" + this.yBarWidth + "," + this.topOffset + ")");

        var format = d3.format(".4f");

        var x = d3.scale.linear()
            .range([0, this.w - this.yBarWidth - 5*this.fontpixels])
            .domain([0, 1]);

        var y = d3.scale.ordinal()
            .rangeRoundBands([this.h, 0])
            .domain(this.barChartData.map(function(d) { return d.name; }));

        var xAxis = d3.svg.axis()
            .scale(x)
            .orient("top")
            .innerTickSize(5)
            .outerTickSize(1);

        var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .innerTickSize(5)
            .outerTickSize(1);

        // selection for bars
        var barSelection = this._svgContainer.selectAll("g.bar").data(this.barChartData, function(d) { return d.name; });

        // create elements (bars)
        var barItems = barSelection
            .enter()
            .append("g")
            .attr("class", "bar")
            .attr("transform", function(d) { return "translate(0," + y(d.name) + ")"; });

        // create bars and texts
        barItems.append("rect")
            .attr("width", function(d) { return x(d.value); })
            .attr("height", this.barHeight);

        barItems.append("text")
            .attr("class", "value")
            .attr("x", function(d) { return x(d.value); })
            .attr("y", y.rangeBand() / 2)
            .attr("dx", function(d) { return d.value > .1 ? -3 : "4em"; })
            .attr("dy", ".35em")
            .attr("text-anchor", "end")
            .text(function(d) { return format(d.value); });

        // remove elements
        barSelection.exit().remove();

        this._svg.selectAll("g.y.axis")
            .call(yAxis);

        this._svg.selectAll("g.x.axis")
            .call(xAxis);

        this.h = this.barChartData.length * 1.2 * this.barHeight + this.topOffset;

        this._svgContainer
            .attr("height", this.h)
            .attr("width", this.w);

        this._svg
            .attr("height", this.h)
            .attr("width", this.w);

        // tooltip
        var tooltip = this._svg.selectAll(".tooltip").data([1]);

        // create tooltip
        tooltip
            .enter()
            .append('text')
            .attr('class', 'tooltip')
            .style('display', 'none')
            .style('fill', '#89a35c')
            .style('z-index', 1000000)
            .style('font-family', 'sans-serif')
            .style('font-size', '13px')
            .style('font-weight', 'bold');

        tooltip.exit().remove();

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

    methods : [ ],

    events: [ 'Selection' ]

} );