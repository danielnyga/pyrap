// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_radar = {};

pwt_radar.RadarChart = function( parent, cssid, options) {

    this._cfg = {
         radius: 5,
         w: 600,
         h: 600,
         factor: 1,
         factorLegend: .85,
         levels: 6,
         maxValues: {},// mapping axis name to max value
         minValues: {},// mapping axis name to min value
         radians: 2 * Math.PI,
         intWidth: 10,
         intCol: 'red',
         opacityArea: 0.5,
         ToRight: 5,
         TranslateX: 80,
         TranslateY: 30,
         ExtraWidthX: 100,
         ExtraWidthY: 100,
         color: d3.scale.category10()
	};


    this._parentDIV = this.createElement(parent);
    this._colorscale = d3.scale.category10();
    this._tooltip;
    this._data = [];
    this._allAxis = [];
    this._total = this._allAxis.length;
    this._radius = this._cfg.factor*Math.min(this._cfg.w/2, this._cfg.h/2);


    // update default options with user defined settings
	if(options){
	  for(var i in options){
		if('undefined' !== typeof options[i]){
		  this._cfg[i] = options[i];
		}
	  }
	}

    this._svg = d3.select(this._parentDIV).append("svg");
    if (cssid) {
        this._svg.attr('id', cssid);
    }
    this._svgContainer = this._svg.select('g.radar');


    this._needsLayout = true;
    this._needsRender = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( that._needsLayout ) {
                that.initialize( that );
                that._needsLayout = false;
            }
            that.update();
            that._needsRender = false;
        }
    } );
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
};

pwt_radar.RadarChart.prototype = {

    initialize: function() {
        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'radar')
                .attr("transform", "translate(" + this._cfg.TranslateX + "," + this._cfg.TranslateY + ")");
                this._svgContainer = this._svg.select('g.radar');
        }
        this.update();
    },

    /**
     * default format string as percentage, otherwise as float with one
     * decimal place with the unit appended.
     */
    Format : function(unit, value){
        if (unit == '%') {
			return d3.format('%')(value);
		} else {
			return d3.format(Math.round(value) == value ? '' : '.1f')(value) + unit;
		}
    },

    wraptext : function(text, width) {
        text.each(function() {
            var text = d3.select(this),
            words = text.text().split(/\s+/),
            y = text.attr("y"),
            lineHeight = 1.1, // ems
            l = [],
            lines = [],
            curs = '',
            c = document.createElement("canvas"),
            ctx = c.getContext("2d");
            ctx.font = "12px DejaVu Serif";

            for (var x = 0; x<words.length; x++) {
                l.push(words[x]);
                if (ctx.measureText(l.join(" ")).width <= width) {
                    curs = l.join(" ");
                } else {
                    l = [words[x]];
                    lines.push(curs);
                }
            }
            lines.push(curs);
            text.text('');
            for (var y = 0; y<lines.length; y++) {
                text.append("tspan")
                    .attr("x", text.attr("x"))
                    .attr("y", text.attr("y"))
                    .attr("dy", y * lineHeight + parseFloat(text.attr("dy") || 0) + "em")
                    .text(lines[y]);
            }
        });
    },

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = "100%";
        element.style.height = "100%";
        parent.append( element );
        return element;
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
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

    /**
     * removes data points from chart
     */
    clear : function () {
        this._data = [];
        this.update();
    },

    /**
     * updates data and legend options
     */
    updateData : function ( data ) {
        // determine min and max values for each axis
        for (var x = 0; x < data.length; x++) {
            for (var y = 0; y < data[x].length; y++) {
                this._cfg.minValues[data[x][y].axis] = typeof this._cfg.minValues[data[x][y].axis] !== 'undefined' ? Math.min(this._cfg.minValues[data[x][y].axis], data[x][y].value) : data[x][y].value;
                this._cfg.maxValues[data[x][y].axis] = typeof this._cfg.maxValues[data[x][y].axis] !== 'undefined' ? Math.max(this._cfg.maxValues[data[x][y].axis], data[x][y].value) : data[x][y].value;
            }
	    }

        this._allAxis = (data[0].map(function(i, j){return i.axis}));
        this._total = this._allAxis.length;
        this._radius = this._cfg.factor*Math.min(this._cfg.w/2, this._cfg.h/2);
        this._data = data;

        this.update();
    },

    /**
     * redraws the graph with the updated nodes and links
     */
    update : function () {
        var that = this;

        // prepare dataset such that levellines and leveltexts can be drawn
        // within one enter() call
        var newaxis = [];
        for(var j = 0; j < this._cfg.levels; j++) {
            for (var x = 0; x < this._allAxis.length; x++){
                var levelFactorLine = this._cfg.factor*this._radius*((j+1)/this._cfg.levels);
                var levelFactorText = this._cfg.factor*this._radius*((j)/this._cfg.levels);
                var value = (j)*(this._cfg.maxValues[this._allAxis[x]]-this._cfg.minValues[this._allAxis[x]])/this._cfg.levels + this._cfg.minValues[this._allAxis[x]];
                newaxis.push([this._allAxis[x], levelFactorLine, levelFactorText, value]);
            }
        }

        // draw circular segments for the levels
        var levellines = this._svgContainer.selectAll(".levelline").data(newaxis);
        levellines.enter()
            .append("svg:line")
            .attr("x1", function(d, i){return d[1]*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
            .attr("y1", function(d, i){return d[1]*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
            .attr("x2", function(d, i){return d[1]*(1-that._cfg.factor*Math.sin((i+1)*that._cfg.radians/that._total));})
            .attr("y2", function(d, i){return d[1]*(1-that._cfg.factor*Math.cos((i+1)*that._cfg.radians/that._total));})
            .attr("class", "levelline")
            .style("stroke", "grey")
            .style("stroke-opacity", "0.75")
            .style("stroke-width", "0.3px")
            .attr("transform", function(d, i){
                return "translate(" + (that._cfg.w/2-d[1]) + ", " + (that._cfg.h/2-d[1]) + ")";
            });

        levellines.exit().remove();

        // draw text indicating at what value each level is
        var leveltext = this._svgContainer.selectAll(".leveltext").data(newaxis);
        leveltext.enter()
            .append("svg:text")
            .attr("x", function(d, i){return d[2]*(1-that._cfg.factor*Math.sin((i)*that._cfg.radians/that._total));})
            .attr("y", function(d, i){return d[2]*(1-that._cfg.factor*Math.cos((i)*that._cfg.radians/that._total));})
            .attr("class", "leveltext")
            .style("font-family", "sans-serif")
            .style("font-size", "8px")
            .attr("transform", function(d, i){
                return "translate(" + (that._cfg.w/2-d[2] + that._cfg.ToRight) + ", " + (that._cfg.h/2-d[2]) + ")";
            })
            .attr("fill", "#737373")
            .text(function(d, i) {
                if (that._cfg.units == null){
                    return that.Format('%', d[3]);
                } else {
                    return that.Format(that._cfg.units[d[0]], d[3]);
                }
            });

        leveltext.exit().remove();

        // draw axes
        var axis = that._svgContainer.selectAll(".axis")
            .data(this._allAxis);

        var axisenter = axis
            .enter()
            .append("g")
            .attr("class", "axis");

        axisenter.append("line")
            .attr("x1", this._cfg.w/2)
            .attr("y1", this._cfg.h/2)
            .attr("x2", function(d, i){return that._cfg.w/2*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
            .attr("y2", function(d, i){return that._cfg.h/2*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
            .attr("class", "line")
            .style("stroke", "grey")
            .style("stroke-width", "1px");

        axisenter.append("text")
            .attr("class", "legend")
            .text(function(d){return d})
            .style("font-family", "sans-serif")
            .style("font-size", "11px")
            .attr("text-anchor", "middle")
            .attr("dy", "1.5em")
            .attr("transform", function(d, i){return "translate(0, -10)"})
            .attr("x", function(d, i){return that._cfg.w/2*(1-that._cfg.factorLegend*Math.sin(i*that._cfg.radians/that._total))-60*Math.sin(i*that._cfg.radians/that._total);})
            .attr("y", function(d, i){return that._cfg.h/2*(1-Math.cos(i*that._cfg.radians/that._total))-20*Math.cos(i*that._cfg.radians/that._total);});

        // draw intervals (only if required)
        if('undefined' !== typeof this._cfg.intervals) {
            axisenter.append("rect")
                .attr("x", function(d, i){return that._cfg.w/2;})
                .attr("y", function(d, i){
                    var linearScale = d3.scale.linear()
                        .domain([that._cfg.minValues[d],that._cfg.maxValues[d]])
                        .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
                    return that._cfg.h/2 + linearScale(that._cfg.intervals[d][0]);
                })
                .attr("transform", function(d, i){
                    var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
                    return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth/2 + ", 0)";
                })
                .attr("fill", that._cfg.intCol)
                .style("fill-opacity", that._cfg.opacityArea)
                .attr("width", that._cfg.intWidth)
                .attr("height", function(d, i) {
                    var linearScale = d3.scale.linear()
                        .domain([that._cfg.minValues[d],that._cfg.maxValues[d]])
                        .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
                    return linearScale(that._cfg.intervals[d][1])-linearScale(that._cfg.intervals[d][0]);
                });
        }

        axis.exit().remove();

        // calculate positions of data points
        series = 0;
        this._data.forEach(function(y, x){
            dataValues = [];
            that._svgContainer.selectAll(".nodes")
                .data(y, function(j, i){
                    var linearScale = d3.scale.linear()
                        .domain([that._cfg.minValues[j.axis],that._cfg.maxValues[j.axis]])
                        .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
                    dataValues.push([
                        that._cfg.w/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total)),
                        that._cfg.h/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total))
                    ]);
                });
            dataValues.push(dataValues[0]); // close polygon

            // draw polygons
            var polygons = that._svgContainer.selectAll(".polygon-radar-chart-serie"+series).data([dataValues]);

            polygons
                .enter()
                .append("polygon")
                .attr("class", "polygon-radar-chart-serie"+series)
                .style("stroke-width", "2px")
                .style("stroke", that._cfg.color(series))
                .attr("points",function(d) {
                    var str="";
                    for(var pti=0;pti<d.length;pti++){
                        str=str+d[pti][0]+","+d[pti][1]+" ";
                    }
                    return str;
                })
                .style("fill", function(j, i){return that._cfg.color(series)})
                .style("fill-opacity", that._cfg.opacityArea)
                .on('mouseover', function (d){
                    z = "polygon."+d3.select(this).attr("class");
                    that._svgContainer.selectAll("polygon")
                        .transition(200)
                        .style("fill-opacity", 0.1);
                    that._svgContainer.selectAll(z)
                        .transition(200)
                        .style("fill-opacity", .7);
                })
                .on('mouseout', function(){
                    that._svgContainer.selectAll("polygon")
                        .transition(200)
                        .style("fill-opacity", that._cfg.opacityArea);
                });
            series++;
            polygons.exit().remove();
        });

        // draw circles at data point positions
        series=0;
        this._data.forEach(function(y, x){
            var datapoints = that._svgContainer.selectAll(".circle-radar-chart-serie"+series).data(y);

            datapoints.enter()
                .append("svg:circle")
                .attr("class", "circle-radar-chart-serie"+series)
                .attr('r', that._cfg.radius)
                .attr("alt", function(j){return Math.max(j.value, 0)})
                .attr("cx", function(j, i){
                    var linearScale = d3.scale.linear()
                        .domain([that._cfg.minValues[j.axis],that._cfg.maxValues[j.axis]])
                        .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
                    dataValues.push([
                        that._cfg.w/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total)),
                        that._cfg.h/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total))
                    ]);
                    return that._cfg.w/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
                })
                .attr("cy", function(j, i){
                    var linearScale = d3.scale.linear()
                        .domain([that._cfg.minValues[j.axis],that._cfg.maxValues[j.axis]])
                        .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
                    return that._cfg.h/2*(1-(parseFloat(linearScale(j.value))/linearScale(that._cfg.maxValues[j.axis]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
                })
                .attr("data-id", function(j){return j.axis})
                .style("fill", that._cfg.color(series)).style("fill-opacity", .9)
                .on('mouseover', function (d){
                    newX =  parseFloat(d3.select(this).attr('cx')) - 10;
                    newY =  parseFloat(d3.select(this).attr('cy')) - 5;

                    tooltip
                        .attr('x', newX)
                        .attr('y', newY)
                        .text(that._cfg.units == null ? that.Format('%', d.value) : that.Format(that._cfg.units[d.axis], d.value))
                        .transition(200)
                        .style('opacity', 1);

                    z = "polygon."+d3.select(this).attr("class");
                    that._svgContainer.selectAll("polygon")
                        .transition(200)
                        .style("fill-opacity", 0.1);
                    that._svgContainer.selectAll(z)
                        .transition(200)
                        .style("fill-opacity", .7);
                })
                .on('mouseout', function(){
                    tooltip
                        .transition(200)
                        .style('opacity', 0);
                    that._svgContainer.selectAll("polygon")
                        .transition(200)
                        .style("fill-opacity", that._cfg.opacityArea);
                })
                .append("svg:title")
                .text(function(j){return j.value});

            series++;
            datapoints.exit().remove();
        });

        // tooltip
        tooltip = this._svgContainer.selectAll(".tooltip").data([1]);
        tooltip
            .enter()
            .append('text')
            .attr('class', 'tooltip')
            .style('opacity', 0)
            .style('font-family', 'sans-serif')
            .style('font-size', '13px');

        tooltip.exit().remove();
    },

    /**
     * update Legend
     */
    updateLegend : function ( legend ) {
        var opts = legend.opts || [];
        var txt = legend.txt || '';

        if (typeof  legend.opts !== 'undefined'){

            var w = 500;
            var h = 500;
            var that = this;

            this._svg
                .append('svg')
                .attr('id', 'radarlegend')
                .attr("width", w + 300)
                .attr("height", h);

            this._legendsvg = this._svg.selectAll('#radarlegend');

            //Create the title for the legend
            var legendtitle = this._legendsvg.selectAll('legendtitle').data([0]);
            legendtitle
                .enter()
                .append("text")
                .attr("class", "legendtitle")
                .attr('transform', 'translate(90,0)')
                .attr("x", w - 70)
                .attr("y", 10)
                .attr("font-size", "12px")
                .attr("fill", "#404040")
                .text(txt)
                .call(that.wraptext, 300);

            legendtitle.exit().remove();

            //Initiate Legend
            this._legendsvg.append("g")
                .attr("height", 100)
                .attr("width", 200)
                .attr('transform', 'translate(90, 40)');

            //Create colour squares
            var legendrect = this._legendsvg.select('g').selectAll('rect').data(opts);
            legendrect
                .enter()
                .append("rect")
                .attr("x", w - 65)
                .attr("y", function(d, i){ return i * 20;})
                .attr("width", 10)
                .attr("height", 10)
                .style("fill", function(d, i){return that._cfg.color(i);});

            legendrect.exit().remove();

            //Create text next to squares
            var legendtext = this._legendsvg.select('g').selectAll('text').data(opts);
            legendtext
                .enter()
                .append("text")
                .attr("x", w - 52)
                .attr("y", function(d, i){ return i * 20 + 9;})
                .attr("font-size", "11px")
                .attr("fill", "#737373")
                .text(function(d) { return d; });

            legendtext.exit().remove();
        }
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadarChart', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_radar.RadarChart( parent, properties.cssid, properties.options);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height'],

  methods : [ 'updateData', 'updateLegend' ],

  events: [ ]

} );