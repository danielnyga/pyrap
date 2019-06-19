/*
 * -*- coding: utf-8 -*-
 *                                          _..._                       .-'''-.
 *                                       .-'_..._''.           .---.   '   _    \
 *  __  __   ___                       .' .'      '.\          |   | /   /` '.   \
 * |  |/  `.'   `.                    / .'                     |   |.   |     \  '
 * |   .-.  .-.   '              .|  . '                       |   ||   '      |  '
 * |  |  |  |  |  |    __      .' |_ | |                 __    |   |\    \     / /
 * |  |  |  |  |  | .:--.'.  .'     || |              .:--.'.  |   | `.   ` ..' /
 * |  |  |  |  |  |/ |   \ |'--.  .-'. '             / |   \ | |   |    '-...-'`
 * |  |  |  |  |  |`" __ | |   |  |   \ '.          .`" __ | | |   |
 * |__|  |__|  |__| .'.''| |   |  |    '. `._____.-'/ .'.''| | |   |
 *                 / /   | |_  |  '.'    `-.______ / / /   | |_'---'
 *                 \ \._,\ '/  |   /              `  \ \._,\ '/
 *                  `--'  `"   `'-'                   `--'  `"
 * (C) 2017 by Mareike Picklum (mareikep@cs.uni-bremen.de)
 *
 * Permission is hereby granted, free of charge, to any person obtaining
 * a copy of this software and associated documentation files (the
 * "Software"), to deal in the Software without restriction, including
 * without limitation the rights to use, copy, modify, merge, publish,
 * distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so, subject to
 * the following conditions:
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 * IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
 * CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
 * TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

pwt_heatmap = {};

pwt_heatmap.Heatmap = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'heatmaptooltip')
        .style('z-index', 1000000);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.heatmap');

    this._cfg = {
         margin: {top: 20, right: 20, bottom: 20, left: 20},
         w: 300,
         h: 300,
         color: d3.scaleSequential()
                    .interpolator(d3.interpolateYlOrBr)
                    .domain([1,100])
        // color: d3.scale.ordinal()
        //     .range(d3.YlOrBr[15])
            // .range(['#e41a1c','#0a4db8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999',
            //     '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd',
            //     '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
            //     '#17becf', '#9edae5'])
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

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append("svg:g")
                .attr('class', 'heatmap')
                .attr("transform", "translate(" + this._cfg.margin.left + "," + this._cfg.margin.top + ")");
            this._svgContainer = this._svg.select('g.heatmap');

            // append x-labels
            this._x_labels = this._svgContainer.append("g")
                .attr("transform", "translate(0," + this._cfg.h + ")");

            // append y-labels
            this._y_labels = this._svgContainer.append("g");
        }
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
            this._cfg.w = Math.min(args[2],args[3]) - 80;
            this._cfg.h = Math.min(args[2],args[3]) - 80;
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
        rwt.remote.Connection.getInstance().getRemoteObject(this).set(args.type, this._svg.node().outerHTML);
    },

    /**
     * updates data options
     */
    setData: function (data) {
        // preprocess data
        this._data = data;
        this._X = d3.map(data, function (d) { return d.x; }).keys();
        this._Y = d3.map(data, function (d) { return d.y; }).keys();
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

        console.log('HEATMAP', this._cfg.h, this._X, this._Y, this._data);
        var x = d3.scaleBand()
            .range([0, this._cfg.h])
            .domain(this._X)
            .padding(0.05);

        var y = d3.scaleBand()
            .range([this._cfg.h, 0])
            .domain(this._Y)
            .padding(0.05);

        // this._x_labels
        //     .attr("transform", "translate(0," + this._cfg.h + ")")
        //     // .call(d3.axisBottom(x).tickSize(0))
        //     .call(d3.axis(x).tickSize(0))
        //     .select(".domain").remove();
        //
        // this._y_labels
        //     // .call(d3.axisLeft(y).tickSize(0))
        //     .call(d3.axis(y).tickSize(0))
        //     .select(".domain").remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE SQUARES                             ///
        ////////////////////////////////////////////////////////////////////////
        var hm = this._svg.selectAll('rect').data(this._data, function (d) {
            return d.x + ':' + d.y;
        });

        hm
            .attr("x", function (d) {
                return x(d.x)
            })
            .attr("y", function (d) {
                return y(d.y)
            })
            .style("fill", function (d) {
                return that._cfg.color(d.value)
            });

        // update
        hm
            .enter()
            .append("rect")
            .attr("x", function (d) {
                return x(d.x)
            })
            .attr("y", function (d) {
                return y(d.y)
            })
            .attr("rx", 4)
            .attr("ry", 4)
            .attr("width", x.bandwidth())
            .attr("height", y.bandwidth())
            .style("fill", function (d) {
                return that._cfg.color(d.value)
            })
            .style("stroke-width", 4)
            .style("stroke", "none")
            .style("opacity", 0.8)
            .on('mouseover', function (d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mouseout', function (d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function (d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html(d.value)
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
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );