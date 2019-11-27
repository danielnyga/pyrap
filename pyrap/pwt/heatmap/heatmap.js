pwt_heatmap = {};

pwt_heatmap.Heatmap = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3v5.select(this._parentDIV).append("div")
        .attr('class', 'heatmaptooltip')
        .style('z-index', 1000000);

    this._svg = d3v5.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.heatmap');

    this._cfg = {
         margin: {top: 0, right: 25, bottom: 60, left: 100, legendwidth: 50},
         w: 300,
         h: 300,
         limits: {min: 0, max: 1},
         color: d3v5.scaleSequential()
                    .interpolator(d3v5.interpolateYlOrBr)
                    .domain([0, 1])
	};

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

pwt_heatmap.Heatmap.prototype = {

    initialize: function () {

        var that = this;

        this._legendgroup = this._svg
            .append('g')
            .attr("transform", "translate(" + (this._cfg.w + this._cfg.margin.legendwidth) + ", 5)")
            .attr("class", "legendaxis");

        this._legendaxisgroup = this._legendgroup
            .append('g')
            .attr("transform", "translate(10,0)")
            .attr("class", "legendaxisgroup");

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .style('position', 'absolute')
                .append("svg:g")
                .attr('class', 'heatmap')
                .attr("transform", "translate(" + (this._cfg.margin.left) + "," + this._cfg.margin.top + ")");
            this._svgContainer = this._svg.select('g.heatmap');

            // append x-labels
            this._x_labels = this._svgContainer.append("g")
                .attr("transform", "translate(0," + (this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom) + ")");

            // append y-labels
            this._y_labels = this._svgContainer.append("g");
        }

        this._defs = this._svgContainer.append("defs");
        this._gradient = this._defs.append('linearGradient')
            .attr('id', 'gradient')
            .attr("x1", "0%")
            .attr("y1", "0%")
            .attr("x2", "0%")
            .attr("y2", "100%");

        d3v5.range(this._cfg.limits.min, this._cfg.limits.max, 0.001)
        .forEach(function (d, i) {
            that._gradient.append('stop')
                .attr("offset", i/(that._cfg.limits.max - that._cfg.limits.min)/10+"%")
                .attr("stop-color", that._cfg.color(Math.abs(d)));
        });

    },

    createElement: function (parent) {
        var clientarea = parent.getClientArea();
        var element = document.createElement("div");
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = clientarea[2];
        element.style.height = clientarea[3];
        parent.append(element);
        return element;
    },

    setBounds: function (args) {
        if (typeof args[2] != 'undefined' && typeof args[3] != 'undefined' ) {
            this._cfg.w = Math.min(args[2], args[3]);// - this._cfg.margin.left - this._cfg.margin.right;
            this._cfg.h = Math.min(args[2], args[3]);// - this._cfg.margin.top - this._cfg.margin.bottom;
        }

        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
        this.update();
    },

    setZIndex: function (index) {
        this._parentDIV.style.zIndex = index;
    },

    destroy: function () {
        var element = this._parentDIV;
        if (element.parentNode) {
            element.parentNode.removeChild(element);
        }
    },

    setWidth: function (width) {
        this._parentDIV.style.width = width + "px";
        this._cfg.w = width;
        this.update();
    },

    setHeight: function (height) {
        this.this._parentDIV.style.height = height + "px";
        this._cfg.h = height;
        this.update();
    },

    /**
     * removes all axes from the radar chart
     */
    clear: function () {
        this.setData({});
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg: function (args) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, [this._svg.node().outerHTML, args.fname] );
    },

    /**
     * updates data options
     */
    setData: function (data) {
        // preprocess data
        this._data = data;
        this._min = data.reduce((min, p) => p.value < min ? p.value : min, data[0].value);
        this._max = data.reduce((max, p) => p.value > max ? p.value : max, data[0].value);
        this._X = d3v5.map(data, function (d) { return d.x; }).keys();
        this._Y = d3v5.map(data, function (d) { return d.y; }).keys();
        this.update();
    },


    /**
     * updates limits
     */
    setLimits: function (limits) {
        this._cfg.limits.min = limits[0];
        this._cfg.limits.max = limits[1];
        this.update();
    },

    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update: function () {

        // no update before graph has been initialized
        if (!this._initialized) {
            return;
        }

        var that = this;

        var x = d3v5.scaleBand()
            .range([0, this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom])
            .domain(this._X)
            .padding(0.03);

        var y = d3v5.scaleBand()
            .range([this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom, 0])
            .domain(this._Y)
            .padding(0.03);

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LEGEND                              ///
        ////////////////////////////////////////////////////////////////////////
        var lx = d3v5.scaleLinear().domain([this._cfg.limits.min, this._cfg.limits.max]).range([0, this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom]);

        this._legendgroup
            .attr("transform", "translate(" + (this._cfg.w + this._cfg.margin.legendwidth) + ", 5)");

        var grad = this._legendgroup.selectAll('rect').data([0,1]);

        grad
            .enter()
            .append("rect")
            .attr("width", 10)
            .attr("height", this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom)
            .style("fill", "url(#gradient)");

        grad
            .attr("height", this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom);

        grad
            .exit().remove();

        var grad2 = this._legendaxisgroup.selectAll('rect').data([0]);

        grad2
            .enter()
            .append("rect")
            .attr("width", 10)
            .attr("height", this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom)
            .style("fill", "none");

        grad2
            .attr("height", this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom);


        grad2
            .exit().remove();


        this._legendaxisgroup
            .call(d3v5.axisRight(lx));


        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LABELS                              ///
        ////////////////////////////////////////////////////////////////////////
        this._x_labels
            .attr("transform", "translate(0," + (this._cfg.h - this._cfg.margin.top - this._cfg.margin.bottom) + ")")
            .call(d3v5.axisBottom(x).tickSize(0))
            .selectAll("text")
                .style("text-anchor", "end")
                .attr("dx", "-.8em")
                .attr("dy", ".15em")
                .attr("transform", "rotate(-35)")
            .select(".domain").remove();

        this._y_labels
            .attr("transform", "translate(0, " + (this._cfg.margin.top) + ")")
            .call(d3v5.axisLeft(y).tickSize(0))
            .select(".domain").remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE SQUARES                             ///
        ////////////////////////////////////////////////////////////////////////
        var hm = this._svgContainer.selectAll('rect').data(this._data, function (d) {
            return d.x + ':' + d.y;
        });

        // update squares
        hm
            .attr("x", function (d) {
                return x(d.x);
            })
            .attr("y", function (d) {
                return y(d.y);
            })
            .attr("width", x.bandwidth())
            .attr("height", y.bandwidth())
            .style("fill", function (d) {
                return that._cfg.color(Math.abs(d.value));
            });

        // create squares
        hm
            .enter()
            .append("rect")
            .attr("x", function (d) {
                return x(d.x);
            })
            .attr("y", function (d) {
                return y(d.y);
            })
            .attr("rx", 4)
            .attr("ry", 4)
            .attr("width", x.bandwidth())
            .attr("height", y.bandwidth())
            .style("fill", function (d) {
                return that._cfg.color(Math.abs(d.value));
            })
            .style("stroke-width", 4)
            .style("stroke", "none")
            .style("opacity", 0.8)
            .on('mouseover', function (d) {
                d3v5.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mouseout', function (d) {
                d3v5.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function (d) {
                var newX = (d3v5.event.pageX + 20);
                var newY = (d3v5.event.pageY - 20);

                that._tooltip
                    .html(d.x + ' - ' + d.y + ': <br>' + d.value)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");

            });

        hm.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Heatmap', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_heatmap.Heatmap( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds', 'limits'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );