// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_radar_red = {};

pwt_radar_red.RadarChartRed = function( parent, options) {

    legendtext = options.legendtext;
    radaroptions = options.radaroptions;

    this._cfg = {
         radius: 150,       //Radius of the outermost circle
         w: 300,            //Width of the circle
	     h: 300,			//Height of the circle
         factor: 1,
         factorLegend: .85,
         labelFactor: 1.25, //How much farther than the radius of the outer circle should the labels be placed
         levels: 6,         //How many levels or inner circles should there be drawn
         maxValues: {},     // mapping axis name to max value
         minValues: {},     // mapping axis name to min value
         margin: {top: 20, right: 20, bottom: 20, left: 20}, //The margins of the SVG
         radians: 2 * Math.PI,
         intWidth: 10,
         intCol: 'red',
         opacityArea: 0.5,  //The opacity of the area of the blob
         opacityCircles: .1,
         ToRight: 5,
         TranslateX: 80,
         TranslateY: 30,
         ExtraWidthX: 100,
         ExtraWidthY: 100,
         color: d3.scale.category10(),
         dotRadius: 5,      //The size of the colored circles of each blog
         roundStrokes: false,
         strokeWidth: 2,
	};


    this._parentDIV = this.createElement(parent);
    this._colorscale = d3.scale.category10();
    this._data = {};
    this._allAxis = [];
    this._total = this._allAxis.length;
    this._legendopts = [];
    this._legendtext = legendtext;



    // update default options with user defined settings
	if(radaroptions){
	  for(var i in radaroptions){
		if('undefined' !== typeof radaroptions[i]){
		  this._cfg[i] = radaroptions[i];
		}
	  }
	}

    this._svg = d3.select(this._parentDIV).append("svg");

    this._svgContainer = this._svg.select('g.radar');

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

pwt_radar_red.RadarChartRed.prototype = {

    initialize: function() {

        d3.selection.prototype.moveToFront = function() {
          return this.each(function(){
            this.parentNode.appendChild(this);
          });
        };
        d3.selection.prototype.moveToBack = function() {
            return this.each(function() {
                var firstChild = this.parentNode.firstChild;
                if (firstChild) {
                    this.parentNode.insertBefore(this, firstChild);
                }
            });
        };

        this._svg
            .append('svg')
            .attr('class', 'radarlegend')
            .attr('width', "100%")
            .attr('height', "100%")
            .attr('transform', 'translate('+ (this._cfg.w + this._cfg.margin.left) +',0)')// move legend svg to the top right corner
            .append("text")
            .attr("class", "legendtitle")
            .attr("x", 0)
            .attr("y", 15)
            .attr("font-size", "12px")
            .attr("fill", "#404040")
            .text(this._legendtext)
            .call(this.wraptext, 300);
        this._svgLegend = this._svg.select('svg.radarlegend');

        this._svg
            .attr('width', "100%")
            .attr('height', "100%")
            .append( "svg:g" )
            .attr('class', 'radar')
            .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.margin.left) + "," + (this._cfg.h/2 + this._cfg.margin.top) + ")");

        this._svgContainer = this._svg.select('g.radar');
        this._axisGrid = this._svgContainer.append("g").attr("class", "axisWrapper");

        //Filter for the outside glow
        var filter = this._svgContainer.append('defs').append('filter').attr('id','glow');
        var feGaussianBlur = filter.append('feGaussianBlur').attr('stdDeviation','2.5').attr('result','coloredBlur');
        var feMerge = filter.append('feMerge');
        var feMergeNode_1 = feMerge.append('feMergeNode').attr('in','coloredBlur');
        var feMergeNode_2 = feMerge.append('feMergeNode').attr('in','SourceGraphic');

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

        this._cfg.w = Math.min(args[2],args[3]) - 100;
        this._cfg.h = this._cfg.w;
        this._svgLegend
            .attr('transform', 'translate('+ (this._cfg.w + this._cfg.margin.left) +',0)');

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
        this._parentDIV.style.height = height + "px";
        this._h = height;
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


    /**
     * split long legend text into multiple lines
     */
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

    /**
     * recalculate datapoint positions on drag event
     */
    dragmove : function( d, i ) {

        if (typeof d.axis === 'undefined') {
            var axis = this._allAxis[i];
        } else {
            var axis = d.axis;
        }

	    // endpoint axis
	    var x0 = this._cfg.w/2*(1-this._cfg.factor*Math.sin(i*this._cfg.radians/this._total));
	    var y0 = this._cfg.h/2*(1-this._cfg.factor*Math.cos(i*this._cfg.radians/this._total));

	    // directional vector axis
	    var dx0 = x0 - this._cfg.w/2;
	    var dy0 = y0 - this._cfg.h/2;

	    // x/y coords of mousepointer
	    coordinates = d3.mouse(this._svgContainer.node());
		var mx = this._cfg.w/2 + (this._cfg.w/2 - coordinates[0]);
		var my = this._cfg.h/2 + (this._cfg.h/2 - coordinates[1]);

	    // insert straight line into plane equation and solve for lambda
	    var lambda = (dx0 * mx + dy0 * my - dx0 * this._cfg.w/2 - dy0 * this._cfg.h/2)/(Math.pow(dx0, 2) + Math.pow(dy0, 2));
	    lambda = Math.max(Math.min(0, lambda), -1)

	    // insert lambda into linear equation to get intersection point of plane with line
	    var px = lambda * -dx0 + this._cfg.w/2;
	    var py = lambda * -dy0 + this._cfg.h/2;

	    var linearScale = d3.scale.linear()
	        .domain([0, Math.sqrt(Math.pow(x0 - this._cfg.w/2, 2) + Math.pow(y0 - this._cfg.h/2, 2))])
	        .range([this._cfg.minValues[axis.name], this._cfg.maxValues[axis.name]]);

		// determine new value for by calculating length from center to (px,py)
	    var len = Math.sqrt(Math.pow(px - this._cfg.w/2, 2) + Math.pow(py - this._cfg.h/2, 2));
	    var newValue = linearScale(len);
	    return [px, py, newValue];

	},

    /**
     * set recently dragged datapoint to foreground
     */
	dragend : function( d, i, _this, that ) {

        if (typeof d.axis === 'undefined') {
            var axis = this._allAxis[i];
        } else {
            var axis = d.axis;
        }

        var dragtarget = d3.select(_this);

		dragtarget
			.attr('opacity', 1);

	    var targetclass = dragtarget.attr('class');

	    var tclass = targetclass.split(/[ -]/)[0];

        switch(tclass) {
            case 'circle':
	            var selectiontype = 'circle';
                var dataset = targetclass.split(selectiontype+'-')[1];
                var v = (dragtarget.data()[0]).value;
                var newdata = {'value': dragtarget.data()[0], 'name': that._allAxis[i].name};
                break;
            case 'mininterval':
            case 'maxinterval':
                // endpoint axis
                var x0 = this._cfg.w/2*(1-this._cfg.factor*Math.sin(i*this._cfg.radians/this._total));
                var y0 = this._cfg.h/2*(1-this._cfg.factor*Math.cos(i*this._cfg.radians/this._total));

                // new coords
                var px0 = dragtarget.attr('x');
                var py0 = dragtarget.attr('y');

                var linearScale = d3.scale.linear()
                    .domain([0, Math.sqrt(Math.pow(x0 - this._cfg.w/2, 2) + Math.pow(y0 - this._cfg.h/2, 2))])
                    .range([this._cfg.minValues[axis.name], this._cfg.maxValues[axis.name]]);

                // get length of vector to new position
                var lenx = px0 - that._cfg.w/2;
                var leny = py0 - that._cfg.h/2;
                var l = Math.sqrt(Math.pow(lenx, 2) + Math.pow(leny, 2));

	            var selectiontype = tclass;
                var dataset = d;
                var newdata = Math.round(linearScale(l) * 100) / 100;
        }
		rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'func': 'dragend', 'type': selectiontype, 'dataset': dataset, 'data': newdata } );
	},

    /**
     * returns a copy (by value) of given dict d
     */
    _cpdict : function( d ) {
        var cp = {};
        for (var k in d) {
            cp[k] = d[k];
        }
        return cp;
    },

    /**
     * updates an axis of the radar chart
     */
    updateAxis : function ( data ) {
        console.log('updateAxis');

    },

    /**
     * adds an axis to the radar chart
     */
    addAxis : function ( axis ) {
        // add axis to list of axes
        this._allAxis.push(axis);
        this._total = this._allAxis.length;

        // add min and max values for the new axis
        this._cfg.minValues[axis.name] = (typeof axis.limits[0]) !== 'undefined' ? axis.limits[0]: 0;
        this._cfg.maxValues[axis.name] = (typeof axis.limits[1]) !== 'undefined' ? axis.limits[1]: 100;

        // update
        this.update();
    },

    /**
     * removes an axis from the radar chart
     */
    remAxis : function ( axis ) {
        // TODO: move this to python
        var tmpdata = this._cpdict(this._data);
        var tmpaxes = this._allAxis.slice();
        this.clear();

        function findaxis(a) { return a.name == axis.name; }

        var remaxes = tmpaxes.filter(findaxis);
        for (var x = 0; x<remaxes.length; x++) {
            var idx = tmpaxes.indexOf(remaxes[x])
            if (idx > -1) {
                tmpaxes.splice(idx, 1);
                Object.keys(tmpdata).forEach(function(key, i) {
                   tmpdata[key].splice(idx, 1);
                }, this);
            }
        }
        this._allAxis = tmpaxes;
        this._total = this._allAxis.length;

        // restore min/max values for axes
        for (var a in this._allAxis) {
            this._cfg.minValues[this._allAxis[a].name] = (typeof this._allAxis[a].limits[0]) !== 'undefined' ? this._allAxis[a].limits[0]: 0;
            this._cfg.maxValues[this._allAxis[a].name] = (typeof this._allAxis[a].limits[1]) !== 'undefined' ? this._allAxis[a].limits[1]: 100;
        }

        this.setData(tmpdata);
        rwt.remote.Connection.getInstance().getRemoteObject( this ).notify( "Selection", { 'type': 'remaxis', 'dataset': axis, 'data': this._data } );
    },

    /**
     * removes all axes from the radar chart
     */
    clear : function ( ) {
        // clear legend
        this._legendopts.splice(0, this._legendopts.length);

        // clear graph polygons and circles
        Object.keys(this._data).forEach(function(key, idx) {
            this._svgContainer.selectAll(".polygon-"+key).remove();
            this._svgContainer.selectAll(".circle-"+key).remove();
        }, this);// TODO update this to new layout

        // clear axes
        this._allAxis.splice(0, this._allAxis.length);
        this._total = this._allAxis.length;

        // clear min and max values
        this._cfg.minValues = {};
        this._cfg.maxValues = {};

        // clear data
        this.setData( {} );
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, this._svg.node().outerHTML );
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        // clear old data
        this._legendopts.splice(0, this._legendopts.length);
        Object.keys(this._data).forEach(function(key, idx) {
            this._svgContainer.selectAll(".polygon-"+key).remove();
            this._svgContainer.selectAll(".circle-"+key).remove();
        }, this);
        this._data = data;
        this.updateData();
    },


    /**
     * updates data options
     */
    updateData : function ( ) {

        // determine min and max values for each axis
        // by updating with (possibly available) data
        for (var x in this._data) {
            this._legendopts.push(x);
            for (var y = 0; y < this._data[x].length; y++) {
                this._cfg.minValues[this._allAxis[y].name] = (typeof this._allAxis[y].limits[0] !== 'undefined') ? this._allAxis[y].limits[0] : (typeof this._cfg.minValues[this._allAxis[y].name] !== 'undefined') ? Math.min(this._cfg.minValues[this._allAxis[y].name], this._data[x][y]) : this._data[x][y];
                this._cfg.maxValues[this._allAxis[y].name] = (typeof this._allAxis[y].limits[1] !== 'undefined') ? this._allAxis[y].limits[1] : (typeof this._cfg.maxValues[this._allAxis[y].name] !== 'undefined') ? Math.max(this._cfg.maxValues[this._allAxis[y].name], this._data[x][y]) : this._data[x][y];
            }
	    }
        this.update();
    },

    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        ////////////////////////////////////////////////////////////////////////
        ///                         UPDATE LEGEND                            ///
        ////////////////////////////////////////////////////////////////////////
        if (typeof this._legendopts !== 'undefined'){

            var that = this;

            // initialize legendtitle
            var legendtitle = this._svgLegend.select('.legendtitle');
            legendtitle
                .text(this._legendtext)
                .call(this.wraptext, 300);

            var optsgroup = that._svgLegend.selectAll(".legendopt").data(this._legendopts);

            // create axis group
            var optsenter = optsgroup
                .enter()
                .append("g")
                .attr("class", "legendopt");

            //update options
            optsgroup.select('.box')
                .attr("x", 10)
                .attr("y", function(d, i){ return 50 + (i * 20);})
                .attr("width", 10)
                .attr("height", 10)
                .style("fill", function(d, i){ return that._cfg.color(i);});

            // create options
            optsenter
                .append("rect")
                .attr('class', 'box')
                .attr("x", 10)
                .attr("y", function(d, i){ return 50 + (i * 20);})
                .attr("width", 10)
                .attr("height", 10)
                .style("fill", function(d, i){ return that._cfg.color(i);});


            //Create text next to squares
            optsgroup.select('.legendtext')
                .attr("y", function(d, i){ return 50 + (i * 20) + 9;})
                .text(function(d) { return d; });

            optsenter
                .append("text")
                .attr('class', 'legendtext')
                .attr("x", 25)
                .attr("y", function(d, i){ return 50 + (i * 20) + 9;})
                .attr("font-size", "11px")
                .attr("fill", "#737373")
                .text(function(d) { return d; });

            optsgroup.exit().remove();
        }


        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LEVELS                              ///
        ////////////////////////////////////////////////////////////////////////

        var newaxis = [];
        for(var j = 0; j < this._cfg.levels; j++) {
            for (var x in this._allAxis){
                var levelFactorLine = this._cfg.radius*((j+1)/this._cfg.levels);
                var levelFactorText = this._cfg.radius*((j)/this._cfg.levels);
                var value = (j)*(this._cfg.maxValues[this._allAxis[x].name]-this._cfg.minValues[this._allAxis[x].name])/this._cfg.levels + this._cfg.minValues[this._allAxis[x].name];
                newaxis.push([levelFactorLine, levelFactorText, value]);
            }
        }

        /////////////////////////////////////////////////////////
        /////////////// Draw the Circular grid //////////////////
        /////////////////////////////////////////////////////////

        //Wrapper for the grid & axes
        var circles = this._axisGrid.selectAll(".gridCircle").data(d3.range(1,(that._cfg.levels+1)).reverse());

        var circlesenter = circles.enter()
            .append("circle")
            .attr("class", "gridCircle")
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;})
            .style("fill", "#CDCDCD")
            .style("stroke", "#CDCDCD")
            .style("fill-opacity", this._cfg.opacityCircles)
            .style("filter" , "url(#glow)");

        // update the background circles
        circles.select('.gridCircle')
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;});

        circles.exit().remove();

        var axislabels = this._axisGrid.selectAll(".axisLabel").data(newaxis);

        var labelsenter = axislabels.enter()
           .append("text")
           .attr("class", "axisLabel")
//           .attr("x", 4)
//           .attr("y", function(d){return -d*that._cfg.radius/that._cfg.levels;})
//           .attr("dy", "0.4em")
            .attr("x", function(d, i){console.log(d,i);return d[1]*(1-Math.sin((i)*that._cfg.radians/that._total));})
            .attr("y", function(d, i){return d[1]*(1-Math.cos((i)*that._cfg.radians/that._total));})
            .attr("transform", function(d, i){
                return "translate(" + (-d[1]) + ", " + (-d[1]) + ")";
            })
           .style("font-size", "10px")
           .attr("fill", "#737373")
           .text(function(d,i) { return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]); });

        axislabels.select('.axisLabel')
//           .attr("x", 4)
//           .attr("y", function(d){return -d*that._cfg.radius/that._cfg.levels;})
            .attr("x", function(d, i){return d[1]*(1-that._cfg.factor*Math.sin((i)*that._cfg.radians/that._total));})
            .attr("y", function(d, i){return d[1]*(1-that._cfg.factor*Math.cos((i)*that._cfg.radians/that._total));})
            .attr("transform", function(d, i){
                return "translate(" + (that._cfg.radius-d[1] + that._cfg.ToRight) + ", " + (that._cfg.radius-d[1]) + ")";
            })           .text(function(d,i) { return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]); });

        axislabels.exit().remove();

//        // prepare dataset such that levellines and leveltexts can be drawn
//        // within one enter() call
//        var newaxis = [];
//        for(var j = 0; j < this._cfg.levels; j++) {
//            for (var x in this._allAxis){
//                var levelFactorLine = this._cfg.factor*this._cfg.w/2*((j+1)/this._cfg.levels);
//                var levelFactorText = this._cfg.factor*this._cfg.h/2*((j)/this._cfg.levels);
//                var value = (j)*(this._cfg.maxValues[this._allAxis[x].name]-this._cfg.minValues[this._allAxis[x].name])/this._cfg.levels + this._cfg.minValues[this._allAxis[x].name];
//                newaxis.push([levelFactorLine, levelFactorText, value]);
//            }
//        }
//
//        // draw circular segments for the levels
//        var levellines = this._svgContainer.selectAll(".levelline").data(newaxis);
//
//        levellines
//            .attr("x1", function(d, i){return d[0]*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
//            .attr("y1", function(d, i){return d[0]*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
//            .attr("x2", function(d, i){return d[0]*(1-that._cfg.factor*Math.sin((i+1)*that._cfg.radians/that._total));})
//            .attr("y2", function(d, i){return d[0]*(1-that._cfg.factor*Math.cos((i+1)*that._cfg.radians/that._total));})
//            .attr("transform", function(d, i){
//                return "translate(" + (that._cfg.w/2-d[0]) + ", " + (that._cfg.h/2-d[0]) + ")";
//            });
//
//        levellines.enter()
//            .append("svg:line")
//            .attr("x1", function(d, i){return d[0]*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
//            .attr("y1", function(d, i){return d[0]*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
//            .attr("x2", function(d, i){return d[0]*(1-that._cfg.factor*Math.sin((i+1)*that._cfg.radians/that._total));})
//            .attr("y2", function(d, i){return d[0]*(1-that._cfg.factor*Math.cos((i+1)*that._cfg.radians/that._total));})
//            .attr("class", "levelline")
//            .style("stroke", "grey")
//            .style("stroke-opacity", "0.75")
//            .style("stroke-width", "0.3px")
//            .attr("transform", function(d, i){
//                return "translate(" + (that._cfg.w/2-d[0]) + ", " + (that._cfg.h/2-d[0]) + ")";
//            });
//
//        levellines.exit().remove();
//
//        // draw text indicating at what value each level is
//        var leveltext = this._svgContainer.selectAll(".leveltext").data(newaxis);
//
//        leveltext
//            .attr("x", function(d, i){return d[1]*(1-that._cfg.factor*Math.sin((i)*that._cfg.radians/that._total));})
//            .attr("y", function(d, i){return d[1]*(1-that._cfg.factor*Math.cos((i)*that._cfg.radians/that._total));})
//            .attr("transform", function(d, i){
//                return "translate(" + (that._cfg.w/2-d[1] + that._cfg.ToRight) + ", " + (that._cfg.h/2-d[1]) + ")";
//            })
//            .text(function(d, i) {
//                return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]);
//            });
//
//        leveltext.enter()
//            .append("svg:text")
//            .attr("x", function(d, i){return d[1]*(1-that._cfg.factor*Math.sin((i)*that._cfg.radians/that._total));})
//            .attr("y", function(d, i){return d[1]*(1-that._cfg.factor*Math.cos((i)*that._cfg.radians/that._total));})
//            .attr("class", "leveltext")
//            .style("font-family", "sans-serif")
//            .style("font-size", "8px")
//            .attr("transform", function(d, i){
//                return "translate(" + (that._cfg.w/2-d[1] + that._cfg.ToRight) + ", " + (that._cfg.h/2-d[1]) + ")";
//            })
//            .attr("fill", "#737373")
//            .text(function(d, i) {
//                return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]);
//            });
//
//        leveltext.exit().remove();
//
//        ////////////////////////////////////////////////////////////////////////
//        ///                       UPDATE AXES                                ///
//        ////////////////////////////////////////////////////////////////////////
//        var axis = that._svgContainer.selectAll(".axis").data(this._allAxis);
//
//        // create axis group
//        var axisenter = axis
//            .enter()
//            .append("g")
//            .attr("class", "axis");
//
//        // update axes
//        axis.select('.line')
//            .attr("x1", this._cfg.w/2)
//            .attr("y1", this._cfg.h/2)
//            .attr("x2", function(d, i){return that._cfg.w/2*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
//            .attr("y2", function(d, i){return that._cfg.h/2*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
//
//        // create axes
//        axisenter.append("line")
//            .attr("x1", this._cfg.w/2)
//            .attr("y1", this._cfg.h/2)
//            .attr("x2", function(d, i){return that._cfg.w/2*(1-that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));})
//            .attr("y2", function(d, i){return that._cfg.h/2*(1-that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));})
//            .attr("class", "line")
//            .style("stroke", "grey")
//            .style("stroke-width", "1px");
//
//        // update axis texts
//        axis.select('.legend')
//            .text(function(d){ return d.name; })
//            .attr("transform", function(d, i){return "translate(0, -10)"})
//            .attr("x", function(d, i){return that._cfg.w/2*(1-that._cfg.factorLegend*Math.sin(i*that._cfg.radians/that._total))-60*Math.sin(i*that._cfg.radians/that._total);})
//            .attr("y", function(d, i){return that._cfg.h/2*(1-Math.cos(i*that._cfg.radians/that._total))-20*Math.cos(i*that._cfg.radians/that._total);});
//
//        // create axis texts
//        axisenter.append("text")
//            .attr("class", "legend")
//            .text(function(d){ return d.name; })
//            .style("font-family", "sans-serif")
//            .style("font-size", "11px")
//            .attr("text-anchor", "middle")
//            .attr("dy", "1.5em")
//            .attr("transform", function(d, i){return "translate(0, -10)"})
//            .attr("x", function(d, i){return that._cfg.w/2*(1-that._cfg.factorLegend*Math.sin(i*that._cfg.radians/that._total))-60*Math.sin(i*that._cfg.radians/that._total);})
//            .attr("y", function(d, i){return that._cfg.h/2*(1-Math.cos(i*that._cfg.radians/that._total))-20*Math.cos(i*that._cfg.radians/that._total);})
//            .on('mouseover', function(d) {
//                d3.select(this).style("cursor", "pointer");
//
//                tooltip
//                    .transition(200)
//                    .style("display", "inline");
//            })
//            .on('mouseout', function(){
//                tooltip
//                    .transition(200)
//                    .style("display", "none");
//            })
//            .on('mousemove', function() {
//                var absoluteMousePos = d3.mouse(this);
//                var newX = (absoluteMousePos[0] + 100);
//                var newY = (absoluteMousePos[1] + 50);
//
//                tooltip
//                    .text('Click to remove axis "' + d3.select(this).text() + '"')
//                    .attr('x', (newX) + "px")
//                    .attr('y', (newY) + "px");
//
//            })
//            .on('click', function(d) {
//                tooltip
//                    .transition(200)
//                    .style("display", "none");
//                that.remAxis({ 'name': d3.select(this).text() });
//            });
//
//
//        ////////////////////////////////////////////////////////////////////////
//        ///                       UPDATE INTERVALS                           ///
//        ////////////////////////////////////////////////////////////////////////
//
//        // update interval rectangles
//        axis.select(".interval")
//            .attr("class", function(d, i) { return "interval interval-"+d.name.split(' ').join('_'); })
//            .attr("x", function(d, i){return that._cfg.w/2;})
//            .attr("y", function(d,i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[0]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth/2 + ", 0)";
//            })
//            .attr("height", function(d, i) {
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return linearScale(d.interval[1])-linearScale(d.interval[0]);
//            });
//
//
//        // create interval rectangles
//        axisenter.append("rect")
//            .attr("class", function(d, i) { return "interval interval-"+d.name.split(' ').join('_'); } )
//            .attr("x", function(d, i){return that._cfg.w/2;})
//            .attr("y", function(d, i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[0]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth/2 + ", 0)";
//            })
//            .attr("fill", that._cfg.intCol)
//            .style("fill-opacity", that._cfg.opacityArea)
//            .attr("width", that._cfg.intWidth)
//            .attr("height", function(d, i) {
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return linearScale(d.interval[1])-linearScale(d.interval[0]);
//            })
//            .on('mouseover', function(d) {
//                tooltip
//                    .transition(200)
//                    .style("display", "inline");
//            })
//            .on('mouseout', function(){
//                tooltip
//                    .transition(200)
//                    .style("display", "none");
//            })
//            .on('mousemove', function(d) {
//                var absoluteMousePos = d3.mouse(axis.node());
//                var newX = (absoluteMousePos[0] + 100);
//                var newY = (absoluteMousePos[1] + 50);
//                tooltip
//                    .text("[" + d.interval[0] + ', ' + d.interval[1] +']')
//                    .attr('x', (newX) + "px")
//                    .attr('y', (newY) + "px");
//
//            });
//
//        // update mininterval rectangles
//        axis.select(".mininterval")
//            .attr("class", function(d, i) { return "mininterval mininterval-"+d.name.split(' ').join('_'); } )
//            .attr("x", function(d, i){return that._cfg.w/2;})
//            .attr("y", function(d, i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[0]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth + ", 0)";
//            })
//            .call(d3.behavior.drag()
//                            .origin(Object)
//                            .on("drag", function(d, i) {
//                                var data = that.dragmove(d, i);
//
//                                var lenx = data[0] - that._cfg.w/2;
//                                var leny = data[1] - that._cfg.h/2;
//
//                                var l = Math.sqrt(Math.pow(lenx, 2) + Math.pow(leny, 2));
//
//                                //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
//                                var maxy = that._svgContainer.select(".maxinterval-"+d.name.split(' ').join('_')).attr('y');
//                                var dragTarget = d3.select(this);
//                                dragTarget
//                                    .attr("y", function(d, i){
//                                        return Math.min(that._cfg.h/2 + l, maxy);
//                                    });
//
//                                // update actual interval
//                                that._svgContainer.select(".interval-"+d.name.split(' ').join('_'))
//                                    .attr("y", function(d, i){
//                                        return that._cfg.h/2 + l;
//                                    })
//                                    .attr("height", function(d, i){
//                                        return maxy - (that._cfg.h/2 + l);
//                                    });
//                                d.interval[0] = Math.round(data[2] * 100) / 100;
//                            })
//                            .on('dragend', function(d, i) {
//
//                                var _this = this;
//                                that.dragend(d, i, _this, that);
//                            })
//            );
//
//        // create mininterval rectangles
//        axisenter.append("rect")
//            .attr("class", function(d, i) { return "mininterval mininterval-"+d.name.split(' ').join('_'); } )
//            .attr("x", function(d, i){return that._cfg.w/2;})
//            .attr("y", function(d, i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[0]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth + ", 0)";
//            })
//            .attr("fill", 'grey')
//            .style("fill-opacity", 1)
//            .attr("width", 2*that._cfg.intWidth)
//            .attr("height", 5)
//            .on('mouseover', function(d) {
//                d3.select(this).style("cursor", "pointer");
//            })
//            .on('mouseout', function(d) {
//                d3.select(this).style("cursor", "default");
//            })
//            .call(d3.behavior.drag()
//                            .origin(Object)
//                            .on("drag", function(d, i) {
//                                var data = that.dragmove(d, i);
//
//                                var lenx = data[0] - that._cfg.w/2;
//                                var leny = data[1] - that._cfg.h/2;
//
//                                var l = Math.sqrt(Math.pow(lenx, 2) + Math.pow(leny, 2));
//
//                                //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
//                                var maxy = that._svgContainer.select(".maxinterval-"+d.name.split(' ').join('_')).attr('y');
//                                var dragTarget = d3.select(this);
//                                dragTarget
//                                    .attr("y", function(d, i){
//                                        return Math.min(that._cfg.h/2 + l, maxy);
//                                    });
//
//                                // update actual interval
//                                that._svgContainer.select(".interval-"+d.name.split(' ').join('_'))
//                                    .attr("y", function(d, i){
//                                        return that._cfg.h/2 + l;
//                                    })
//                                    .attr("height", function(d, i){
//                                        return maxy - (that._cfg.h/2 + l);
//                                    });
//                                d.interval[0] = Math.round(data[2] * 100) / 100;
//                            })
//                            .on('dragend', function(d, i) {
//
//                                var _this = this;
//                                that.dragend(d, i, _this, that);
//                            })
//            );
//
//        // update maxinterval rectangles
//        axis.select(".maxinterval")
//            .attr("class", function(d, i) { return "maxinterval maxinterval-"+d.name.split(' ').join('_'); } )
//            .attr("x", function(d, i){ return that._cfg.w/2; } )
//            .attr("y", function(d, i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[1]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth + ", 0)";
//            })
//            .call(d3.behavior.drag()
//                            .origin(Object)
//                            .on("drag", function(d, i) {
//                                var data = that.dragmove(d, i);
//
//                                var lenx = data[0] - that._cfg.w/2;
//                                var leny = data[1] - that._cfg.h/2;
//
//                                var l = Math.sqrt(Math.pow(lenx, 2) + Math.pow(leny, 2));
//
//                                //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
//                                var miny = that._svgContainer.select(".mininterval-"+d.name.split(' ').join('_')).attr('y')
//                                var dragTarget = d3.select(this);
//                                dragTarget
//                                    .attr("y", function(d, i){
//                                        return Math.max(miny, that._cfg.h/2 + l);
//                                    });
//
//                                // update actual interval
//                                that._svgContainer.select(".interval-"+d.name.split(' ').join('_'))
//                                    .attr("height", function(d, i){
//                                        return (that._cfg.h/2 + l) - miny;
//                                    });
//                                d.interval[1] = Math.round(data[2] * 100) / 100;
//                            })
//                            .on('dragend', function(d, i) {
//                                var _this = this;
//                                that.dragend(d, i, _this, that);
//                            })
//            );
//
//
//        // create maxinterval rectangles
//        axisenter.append("rect")
//            .attr("class", function(d, i) { return "maxinterval maxinterval-"+d.name.split(' ').join('_'); })
//            .attr("x", function(d, i){ return that._cfg.w/2; } )
//            .attr("y", function(d, i){
//                var linearScale = d3.scale.linear()
//                    .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
//                    .range([0,Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                return that._cfg.h/2 + linearScale(d.interval[1]);
//            })
//            .attr("transform", function(d, i){
//                var angledeg = (Math.PI - i*that._cfg.radians/that._total) * 180/Math.PI;
//                return "rotate(" + angledeg + ", " + that._cfg.w/2 + ", " + that._cfg.h/2 +") translate(-" + that._cfg.intWidth + ", 0)";
//            })
//            .attr("fill", 'grey')
//            .style("fill-opacity", 1)
//            .attr("width", 2*that._cfg.intWidth)
//            .attr("height", 5)
//            .on('mouseover', function(d) {
//                d3.select(this).style("cursor", "pointer");
//            })
//            .on('mouseout', function(d) {
//                d3.select(this).style("cursor", "default");
//            })
//            .call(d3.behavior.drag()
//                            .origin(Object)
//                            .on("drag", function(d, i) {
//                                var data = that.dragmove(d, i);
//
//                                var lenx = data[0] - that._cfg.w/2;
//                                var leny = data[1] - that._cfg.h/2;
//
//                                var l = Math.sqrt(Math.pow(lenx, 2) + Math.pow(leny, 2));
//
//                                //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
//                                var miny = that._svgContainer.select(".mininterval-"+d.name.split(' ').join('_')).attr('y')
//                                var dragTarget = d3.select(this);
//                                dragTarget
//                                    .attr("y", function(d, i){
//                                        return Math.max(miny, that._cfg.h/2 + l);
//                                    });
//
//                                // update actual interval
//                                that._svgContainer.select(".interval-"+d.name.split(' ').join('_'))
//                                    .attr("height", function(d, i){
//                                        return (that._cfg.h/2 + l) - miny;
//                                    });
//                                d.interval[1] = Math.round(data[2] * 100) / 100;
//                            })
//                            .on('dragend', function(d, i) {
//                                var _this = this;
//                                that.dragend(d, i, _this, that);
//                            })
//            );
//
//        axis.exit().remove();
//
//        ////////////////////////////////////////////////////////////////////////
//        ///                       UPDATE POLYGONS                            ///
//        ////////////////////////////////////////////////////////////////////////
//        var dataValues = []
//        Object.keys(this._data).forEach(function(key, idx) {
//            dataValues.splice(0, dataValues.length);
//            that._svgContainer.selectAll(".nodes")
//                .data(this[key], function(val, i){
//                    var linearScale = d3.scale.linear()
//                        .domain([that._cfg.minValues[that._allAxis[i].name],that._cfg.maxValues[that._allAxis[i].name]])
//                        .range([0, Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                    var x = that._cfg.w/2*(1-(parseFloat(linearScale(val))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
//                    var y = that._cfg.h/2*(1-(parseFloat(linearScale(val))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
//                    // if values are NaN, set to center of axis
//                    dataValues.push([
//                        isNaN(x) ? that._cfg.w/2*(1-(parseFloat(linearScale(val))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total)): x,
//                        isNaN(y) ? that._cfg.h/2*(1-(parseFloat(linearScale(val))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total)): y
//                    ]);
//                });
//            if (typeof dataValues[0] !== 'undefined') {
//                dataValues.push(dataValues[0]); // close polygon
//            }
//
//            // select polygons
//            var polygons = that._svgContainer.selectAll(".polygon-"+that._legendopts[idx]).data([dataValues]);
//
//            // update polygons
//            polygons
//                .attr("points",function(d) {
//                    var str="";
//                    for(var pti=0;pti<d.length;pti++){
//                        str=str+d[pti][0]+","+d[pti][1]+" ";
//                    }
//                    return str;
//                })
//
//            // create polygons
//            polygons
//                .enter()
//                .append("polygon")
//                .attr("class", "polygon-"+that._legendopts[idx])
//                .style("stroke-width", "2px")
//                .style("stroke", that._cfg.color(idx))
//
//                .attr("points",function(d) {
//                    var str="";
//                    for(var pti=0;pti<d.length;pti++){
//                        str=str+d[pti][0]+","+d[pti][1]+" ";
//                    }
//                    return str;
//                })
//                .style("fill", function(j, i){return that._cfg.color(idx)})
//                .style("fill-opacity", that._cfg.opacityArea)
//                .on('mouseover', function (d){
//                    z = "polygon."+d3.select(this).attr("class");
//                    that._svgContainer.selectAll("polygon")
//                        .transition(200)
//                        .style("fill-opacity", 0.1);
//                    that._svgContainer.selectAll(z)
//                        .transition(200)
//                        .style("fill-opacity", .7);
//                    d3.select(this).moveToBack();
//                })
//                .on('mouseout', function(){
//                    that._svgContainer.selectAll("polygon")
//                        .transition(200)
//                        .style("fill-opacity", that._cfg.opacityArea);
//                    d3.select(this).moveToFront();
//                });
//
//            // remove old polygons
//            polygons.exit().remove();
//        }, this._data);
//
//
//
//        ////////////////////////////////////////////////////////////////////////
//        ///                       UPDATE CIRCLES                             ///
//        ////////////////////////////////////////////////////////////////////////
//        Object.keys(this._data).forEach(function(key, idx) {
//            // select datapoints
//            var datapoints = that._svgContainer.selectAll(".circle-"+that._legendopts[idx]).data(this[key]);
//            var cdata = this[key];
//
//            // update datapoints
//            datapoints
//                .attr("cx", function(cval, i){
//                    var linearScale = d3.scale.linear()
//                        .domain([that._cfg.minValues[that._allAxis[i].name],that._cfg.maxValues[that._allAxis[i].name]])
//                        .range([0, Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                    var cx = that._cfg.w/2*(1-(parseFloat(linearScale(cval))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
//                    if (isNaN(cx)) {
//                        cx = that._cfg.w/2*(1-(parseFloat(linearScale(cval))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
//                    }
//                    return cx;
//                })
//                .attr("cy", function(cval, i){
//                    var linearScale = d3.scale.linear()
//                        .domain([that._cfg.minValues[that._allAxis[i].name],that._cfg.maxValues[that._allAxis[i].name]])
//                        .range([0, Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                    var cy = that._cfg.h/2*(1-(parseFloat(linearScale(cval))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
//                    if (isNaN(cy)) {
//                        cy = that._cfg.h/2*(1-(parseFloat(linearScale(cval))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
//                    }
//                    return cy;
//                })
//
//            // create datapoints
//            datapoints.enter()
//                .append("svg:circle")
//                .attr("class", "circle-"+that._legendopts[idx])
//                .attr('r', that._cfg.radius)
//                .attr("alt", function(j){return Math.max(j, 0)})
//                .attr("cx", function(cval, i){
//                    var linearScale = d3.scale.linear()
//                        .domain([that._cfg.minValues[that._allAxis[i].name],that._cfg.maxValues[that._allAxis[i].name]])
//                        .range([0, Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                    var cx = that._cfg.w/2*(1-(parseFloat(linearScale(cval))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
//                    if (isNaN(cx)) {
//                        cx = that._cfg.w/2*(1-(parseFloat(linearScale(cval))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.sin(i*that._cfg.radians/that._total));
//                    }
//                    return cx;
//                })
//                .attr("cy", function(cval, i){
//                    var linearScale = d3.scale.linear()
//                        .domain([that._cfg.minValues[that._allAxis[i].name],that._cfg.maxValues[that._allAxis[i].name]])
//                        .range([0, Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2)]);
//                    var cy = that._cfg.h/2*(1-(parseFloat(linearScale(cval))/linearScale(that._cfg.maxValues[that._allAxis[i].name]))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
//                    if (isNaN(cy)) {
//                        cy = that._cfg.h/2*(1-(parseFloat(linearScale(cval))/Math.abs(that._cfg.h/2*(1-that._cfg.factor) - that._cfg.h/2))*that._cfg.factor*Math.cos(i*that._cfg.radians/that._total));
//                    }
//                    return cy;
//                })
//                .attr("data-id", function(j){return key})
//                .style("fill", that._cfg.color(idx)).style("fill-opacity", .9)
//                .on('mouseover', function(d) {
//                    d3.select(this).style("cursor", "pointer");
//                    tooltip
//                        .transition(200)
//                        .style("display", "inline");
//
//                    z = "polygon."+d3.select(this).attr("class");
//
//                    that._svgContainer.selectAll("polygon")
//                        .transition(200)
//                        .style("fill-opacity", 0.1);
//
//                    that._svgContainer.selectAll(z)
//                        .transition(200)
//                        .style("fill-opacity", .7);
//                })
//                .on('mouseout', function(){
//                    d3.select(this).style("cursor", "default");
//                    tooltip
//                        .transition(200)
//                        .style("display", "none");
//
//                    that._svgContainer.selectAll("polygon")
//                        .transition(200)
//                        .style("fill-opacity", that._cfg.opacityArea);
//                })
//                .on('mousemove', function(d, i) {
//                    var absoluteMousePos = d3.mouse(axis.node());
//                    var newX = (absoluteMousePos[0] + 100);
//                    var newY = (absoluteMousePos[1] + 50);
//                    tooltip
//                        .text(that.Format(that._allAxis[i].unit, d))
//                        .attr('x', (newX) + "px")
//                        .attr('y', (newY) + "px");
//
//                })
//                .call(d3.behavior.drag()
//                                .origin(Object)
//                                .on("drag", function(d, i) {
//                                    var data = that.dragmove(d, i);
//
//                                    //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
//                                    var dragTarget = d3.select(this);
//                                    dragTarget
//                                        .attr("cx", function() { return data[0]; })
//                                        .attr("cy", function() { return data[1]; });
//
//                                    //Updating the data of the circle with the new value
//                                    cdata[i] = Math.round(data[2] * 100) / 100;
//                                    that.update();
//                                })
//                                .on('dragend', function(d, i) {
//                                    var _this = this;
//                                    that.dragend(d, i, _this, that);
//                                })
//                );
//
//            // remove datapoints
//            datapoints.exit().remove();
//        }, this._data);

        // tooltip
        var tooltip = this._svg.selectAll(".tooltip").data([1]);

        // create tooltip
        tooltip
            .enter()
            .append('text')
            .attr('class', 'tooltip')
            .style('display', 'none')
            .style('fill', 'steelblue')
            .style('z-index', 1000000)
            .style('font-family', 'sans-serif')
            .style('font-size', '13px')
            .style('font-weight', 'bold');

        tooltip.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadarChartRed', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_radar_red.RadarChartRed( parent, properties);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height', 'data', 'bounds'],

  methods : [ 'updateData', 'addAxis', 'remAxis', 'clear', 'retrievesvg'],

  events: [ 'Selection' ]

} );