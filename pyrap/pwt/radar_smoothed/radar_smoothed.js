pwt_rs_ = {};

pwt_rs_.RadarSmoothed = function( parent, options ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'rs_tooltip')
        .style('z-index', 1000000);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.rs');
    this._radarlegend = this._svg.select('svg.rs_legend');
    this._id = null;

    this._cfg = {
        w: 800,
        h: 600,
        radius: null,
        angleslice: null,
        intervalwidth: 15,
        top: 50,
        right: 50,
        bottom: 50,
        left: 50,
        levels: 5,              //How many levels or inner circles should there be drawn
        labelFactor: 1.1,   	//How much farther than the radius of the outer circle should the labels be placed
        wrapWidth: 60, 		    //The number of pixels after which a label needs to be given a new line
        opacityArea: 0.35, 	    //The opacity of the area of the blob
        dotRadius: 4, 			//The size of the colored circles of each blog
        strokeWidth: 2, 		//The width of the stroke around each blob
        roundStrokes: true,	    //If true the area and stroke will follow a round path (cardinal-closed)
        color: d3.scale.ordinal()
            .range(['#e41a1c','#0a4db8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999',
                    '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd',
                    '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
                    '#17becf', '#9edae5']),
        maxValues: {},          // mapping axis name to max value
        minValues: {}           // mapping axis name to min value
	};

    this._data = {};
    this._allAxis = [];
    this._allAxisnames = [];
    this._total = this._allAxis.length;
    this._legendopts = [];
    this._legendtext = options.legendtext;

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

pwt_rs_.RadarSmoothed.prototype = {

    initialize: function() {
        this._id = rwt.remote.Connection.getInstance().getRemoteObject( this )._.id;


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

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'rs')
                .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ") scale(1 -1)");
            this._svgContainer = this._svg.select('g.rs');

            this._svg
                .append('svg')
                .attr('class', 'rs_legend')
                .attr('width', "100%")
                .attr('height', "100%")
                .attr('transform', 'translate('+ this._cfg.w +',0)')// move legend svg to the top right corner
                .append("text")
                .attr("class", "rs_legendtitle")
                .attr("x", 0)
                .attr("y", 15)
                .attr("dy", "0.35em")
                .text(this._legendtext)
                .call(this.wrap, 250);
            this._radarlegend = this._svg.select('svg.rs_legend');

        }

        // Glow filter
        this._defs = this._svgContainer
            .append('defs');

        this._filter = this._defs
            .append('filter')
            .attr('id','glow' + this._id);

        this._filter
            .append('feGaussianBlur')
            .attr('stdDeviation','2.5')
            .attr('result','coloredBlur');

        this._femerge = this._filter
            .append('feMerge');

        this._femerge
            .append('feMergeNode')
            .attr('in','coloredBlur');

        this._femerge
            .append('feMergeNode')
            .attr('in','SourceGraphic');

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
        if (typeof args[2] != 'undefined' && typeof args[3] != 'undefined' ) {
            this._cfg.w = args[2] - this._cfg.left - this._cfg.right;
            this._cfg.h = args[3] - this._cfg.top - this._cfg.bottom;
        }

        this._svgContainer
            .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ") scale(1 -1)");

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
        this._cfg.w = width;
        this.update();
    },

    setHeight: function( height ) {
        this.this._parentDIV.style.height = height + "px";
        this._cfg.h = height;
        this.update();
    },

    /**
     * removes all axes from the radar chart
     */
    clear : function ( ) {
        // clear legend
        this._legendopts.splice(0, this._legendopts.length);

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
     * sorts incoming data such that legend is easier to read
     */
    sortOnKeys : function(dict) {

        var sorted = [];
        for(var key in dict) {
            sorted[sorted.length] = key;
        }
        sorted.sort();

        var tempDict = {};
        for(var i = 0; i < sorted.length; i++) {
            tempDict[sorted[i]] = dict[sorted[i]];
        }

        return tempDict;
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        this._legendopts.splice(0, this._legendopts.length);
        this._data = this.sortOnKeys(data);

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
     * generate repl from axisname so it can be used as classname
     * --> required to avoid dots or empty spaces in class names
     */
    replAxisname: function(s){
        return s.split(' ').join('_').split('.').join('-dot-');
    },

    /**
     * default format string as percentage, otherwise as float with one
     * decimal place with the unit appended.
     */
    Format : function(unit, value){
        if (unit === '%') {
			return d3.format('.2%')(value);
		} else {
            return (value >= 0.1 ? d3.format(".2f")(value) : d3.format(".2e")(value)) + unit;
		}
    },

    //Taken from http://bl.ocks.org/mbostock/7555321
    //Wraps SVG text
    wrap : function (text, width) {
        text.each(function() {
        var text = d3.select(this),
            words = text.text().split(/\s+/).reverse(),
            word,
            line = [],
            lineNumber = 0,
            lineHeight = 1.4, // ems
            y = text.attr("y"),
            x = text.attr("x"),
            dy = parseFloat(text.attr("dy")),
            tspan = text.text(null).append("tspan").attr("x", x).attr("y", y).attr("dy", dy + "em");

            while (word = words.pop()) {
                line.push(word);
                tspan.text(line.join(" "));
                if (tspan.node().getComputedTextLength() > width) {
                    line.pop();
                    tspan.text(line.join(" "));
                    line = [word];
                    tspan = text.append("tspan").attr("x", x).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
                }
            }
        });
    },

    /**
     * recalculate datapoint positions on drag event
     */
    dragmove : function( d, i ) {

        var axis;
        if (typeof d.axis === 'undefined') {
            axis = this._allAxis[i];
        } else {
            axis = d.axis;
        }

        // the axis end point
        var x0 = this.valtop(axis, this._cfg.maxValues[axis.name]) * (Math.cos(this._cfg.angleslice*i + Math.PI/2));
        var y0 = this.valtop(axis, this._cfg.maxValues[axis.name]) * (-Math.sin(this._cfg.angleslice*i + Math.PI/2));

	    // x/y coords of mousepointer
	    coordinates = d3.mouse(this._svgContainer.node());
		var mx = coordinates[0];
		var my = coordinates[1];

		// determine the direction of the mouse pointer (positive - mouse moves in direction of axis, negative - mouse
        // moves in opposite direction
        var lambda = Math.sign((x0 * mx + y0 * my)/(Math.pow(x0, 2) + Math.pow(y0, 2)));

		// determine new value for by calculating length from center to (px,py)
        // if the mousepointer is at a position equal to or lower than the axis minimum, the newvalue is set to the
        // axis minimum
	    var len = Math.sqrt(Math.pow(mx, 2) + Math.pow(my, 2));
	    var axvalue = this.ptoval(axis, Math.max(0, len * lambda));

	    // return new x/y position of the dragtarget (and maybe the corresponding interval) and the semantic value at
        // that point of the axis
	    return [mx, my, axvalue];
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
                var newdata = {'value': dragtarget.data()[0], 'name': this._allAxis[i].name};
                break;
            case 'rs_miniv':
            case 'rs_maxiv':

	            var selectiontype = tclass;
                var dataset = d;
                var newdata = this.ptoval(d, dragtarget.attr('y'));
        }
		rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { args: {'func': 'dragend', 'type': selectiontype, 'dataset': dataset, 'data': newdata} } );
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
        for (var x = 0; x < this._allAxis.length; x++) {
            if (this._allAxis[x].name === data.axis.name) {
                this._allAxis[x].unit = data.axis.unit;
                this._allAxis[x].interval = data.axis.interval;
                this._allAxis[x].limits = data.axis.limits;
                break;
            }
        }
        this.update();

    },

    /**
     * adds an axis to the radar chart
     */
    addAxis : function ( axis ) {
        // add axis to list of axes
        this._allAxis.push(axis);
        this._allAxisnames.push(axis.name);
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
    },

    /**
     * interpolates a radial line for the given value
     * @param v
     */
    radarline : function (v) {
        var that = this;
        return d3.svg.line.radial()
            .interpolate(that._cfg.roundStrokes ? "cardinal-closed" : "linear-closed")
            .radius(function(d) { return that.valtop(d[2], d[1]); })
            .angle(function(d,i) { return that._cfg.angleslice*(i+1); })(v);
    },

    /**
     * maps a value along the axis to its semantic value
     * @param d   the axis
     * @param p   the point on the axis to determine its semantic value for
     */
    ptoval : function(d, p) {
        var that = this;
        return d3.scale.linear()
            .domain([0, that._cfg.radius])
            .range([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])(p);
    },

    /**
     * maps the semantic value of an axis to its coordinate - the inverse of ptoval
     * @param d     the axis
     * @param v     the semantic value to determine the coordinate for
     */
    valtop : function(d, v) {
        var that = this;
        return function(x) {
            return d3.scale.linear()
                .domain([that._cfg.minValues[d.name], that._cfg.maxValues[d.name]])
                .range([0, that._cfg.radius])(x);
        }(v);
    },

    /**
     * the rotation angle for the given axis
     * @param i     the index of the axis to determine the angle for
     * @returns {number}
     */
    angledeg : function(i) {
        return (Math.PI - i*this._cfg.angleslice) * 180/Math.PI;
    },

    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        ////////////////////////////////////////////////////////////////////////
        ///                         UPDATE VARIABLES                         ///
        ////////////////////////////////////////////////////////////////////////

        // update translation of main group
        this._svgContainer
                .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ")");

        this._cfg.color
            .domain(Object.keys(this._allAxisnames));

        this._cfg.radius = Math.min(this._cfg.w/2, this._cfg.h/2);	//Radius of the outermost circle
        this._cfg.angleslice = Math.PI * 2 / this._total;		            // The width in radians of each "slice"

        ////////////////////////////////////////////////////////////////////////
        ///                         UPDATE LEGEND                            ///
        ////////////////////////////////////////////////////////////////////////
        if (typeof this._legendopts !== 'undefined'){

            this._radarlegend
                .attr('transform', 'translate('+ this._cfg.w +',0)');// move legend svg to the top right corner

            var legendsvg = this._radarlegend.selectAll('g.rs_legendopts').data(this._legendopts);

            // initialize legendtitle
            var legendtitle = legendsvg.select('.rs_legendtitle');
            legendtitle
                .text(this._legendtext)
                .call(this.wrap, 250);

            var legendsvgenter = legendsvg
                .enter()
                .append('svg:g')
                .attr('class', 'rs_legendopts')
                .attr('transform', 'translate(0, 25)');

            //Create color squares
            var legendrect = legendsvg.select('rect');

            legendrect
                .attr("y", function(d, i){ return i * 20;})
                .style("fill", function(d, i){ return that._cfg.color(i);});

            legendsvgenter
                .append("rect")
                .attr('class', 'rs_legendrect')
                .attr('top', '100px')
                .attr("x", 10)
                .attr("y", function(d, i){ return i * 20;})
                .attr("dy", "0.35em")
                .attr("width", 10)
                .attr("height", 10)
                .style("fill", function(d, i){ return that._cfg.color(i);});

            //Create text next to squares
            var legendtext = legendsvg.select('text');

            legendtext
                .attr("y", function(d, i){ return i * 20 + 9;})
                .text(function(d) { return d; });

            legendsvgenter
                .append("text")
                .attr('class', 'rs_legendtext')
                .attr("x", 25)
                .attr("y", function(d, i){ return i * 20 + 9;})
                .on('click', function(d) {
                    //Dim all blobs
                    that._svgContainer.selectAll(".rs_area")
                        .transition(200)
                        .style("fill-opacity", 0.1);
                    //Bring back the hovered over blob
                    that._svgContainer.select('.rs_area-' + that.replAxisname(d))
                        .transition(200)
                        .style("fill-opacity", 0.7);

                })
                .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                    that._tooltip
                        .transition(200)
                        .style("display", "block");
                })
                .on('mouseout', function(d){
                    d3.select(this).style("cursor", "default");
                    that._tooltip
                        .transition(200)
                        .style("display", "none");
                })
                .on('mousemove', function(d) {
                    var newX = (d3.event.pageX + 20);
                    var newY = (d3.event.pageY - 20);

                    that._tooltip
                        .html('Click to highlight')
                        .style("left", (newX) + "px")
                        .style("top", (newY) + "px");

                })
                .text(function(d) { return d; });

            legendsvg.exit().remove();
        }


        /////////////////////////////////////////////////////////
        /////////////// Draw the Circular grid //////////////////
        /////////////////////////////////////////////////////////
        var axisgrid = this._svgContainer.selectAll('g.rs_levelcircleswrapper').data([0]);

        var axisgridenter = axisgrid
            .enter()
            .append('g')
            .attr('class', 'rs_levelcircleswrapper');

        axisgrid.exit().remove();

        //Draw the background circles
        var axislevels = axisgrid.selectAll(".rs_levelcircle").data(d3.range(1,(this._cfg.levels+1)).reverse());

        axislevels
           .enter()
            .append("circle")
            .attr("class", "rs_levelcircle")
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;})
            .style("filter" , "url(#glow" + this._id + ")");

        axislevels
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;});

        axislevels.exit().remove();


        /////////////////////////////////////////////////////////
        //////////////////// Draw the axes //////////////////////
        /////////////////////////////////////////////////////////

        //Create the straight lines radiating outward from the center
        var axes = axisgrid.selectAll("g.rs_axiswrapper").data(this._allAxis);

        axes.exit().remove();

        var axisenter = axes
            .enter()
            .append('g')
            .attr('class', 'rs_axiswrapper');

        // append the lines
        axisenter
            .append("line")
            .attr("class", "rs_axisline")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor  * (Math.cos(that._cfg.angleslice*i + Math.PI/2)); })
            .attr("y2", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor  * (-Math.sin(that._cfg.angleslice*i + Math.PI/2)); });

        // update the lines
        axes.select(".rs_axisline")
            .attr("x2", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor  * (Math.cos(that._cfg.angleslice*i + Math.PI/2)); })
            .attr("y2", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor  * (-Math.sin(that._cfg.angleslice*i + Math.PI/2)); });

        // append the axis labels
        axisenter
            .append("text")
            .attr("class", "rs_axisname")
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .attr("x", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor * (Math.cos(that._cfg.angleslice*i + Math.PI/2)); })
            .attr("y", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor * (-Math.sin(that._cfg.angleslice*i + Math.PI/2)); })
            .text(function(d, i){return d.name})
            .call(this.wrap, this._cfg.wrapWidth)
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");

                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mouseout', function(d){
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html('<b>' + d.name + '</b> (' + d.unit + ')<br><b>limits:</b> [' + d.limits + ']<br><b>interval:</b> [' + d.interval + ']')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");

            })
            .on('click', function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
                rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'button': 'left', args:{'axis': d3.select(this).text(), 'type': 'axis'} } );
            })
            .on('contextmenu', function(d) {
                rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'button': 'right', args:{'axis': d3.select(this).text(), 'type': 'axis'} } );
            });

        // update the labels
        axes.select(".rs_axisname")
            .attr("x", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor * (Math.cos(that._cfg.angleslice*i + Math.PI/2)); })
            .attr("y", function(d, i){ return that.valtop(d, that._cfg.maxValues[d.name]) * that._cfg.labelFactor * (-Math.sin(that._cfg.angleslice*i + Math.PI/2)); })
            .text(function(d, i){return d.name})
            .call(this.wrap, this._cfg.wrapWidth);

        var newaxis = [];
        for(var j = 0; j <= this._cfg.levels; j++) {
            for (var x in this._allAxis){
                var levelFactorLine = this._cfg.radius*((j+1)/this._cfg.levels);
                var levelFactorText = this._cfg.radius*((j)/this._cfg.levels);
                var value = (j)*(this._cfg.maxValues[this._allAxis[x].name]-this._cfg.minValues[this._allAxis[x].name])/this._cfg.levels + this._cfg.minValues[this._allAxis[x].name];
                newaxis.push([levelFactorLine, levelFactorText, value]);
            }
        }

        //Text indicating at what % each level is
        var axislabels = axes.selectAll(".rs_axislabel").data(newaxis);

        axislabels
           .enter()
            .append("text")
            .attr("class", "rs_axislabel")
            .attr("dy", "0.4em")
            .attr("x", function(d, i){return d[1]*(1-Math.sin((i)*that._cfg.angleslice));})
            .attr("y", function(d, i){return d[1]*(1-Math.cos((i)*that._cfg.angleslice));})
            .attr("transform", function(d, i){
                return "translate(" + -d[1] + ", " + -d[1] + ")";
            })
            .text(function(d, i) {
                return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]);
            });

        axislabels
            .attr("x", function(d, i){return d[1]*(1-Math.sin((i)*that._cfg.angleslice));})
            .attr("y", function(d, i){return d[1]*(1-Math.cos((i)*that._cfg.angleslice));})
            .attr("transform", function(d, i){
                return "translate(" + -d[1] + ", " + -d[1] + ")";
            })
            .text(function(d, i) {
                return that.Format(that._allAxis[i%that._allAxis.length].unit, isNaN(d[2]) ? 0 : d[2]);
            });

        axislabels.exit().remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE INTERVALS                           ///
        ////////////////////////////////////////////////////////////////////////

        // update interval rectangles
        axes.select(".rs_iv")
            .attr("class", function(d, i) { return "rs_iv rs_iv-"+that.replAxisname(d.name); })
            .attr("height", function(d, i) {
                return that.valtop(d, d.interval[1]) - that.valtop(d, d.interval[0]);
            })
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[0]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth/2 + ", 0) ";
            });


        // create interval rectangles
        axisenter.append("rect")
            .attr("class", function(d, i) { return "rs_iv rs_iv-"+that.replAxisname(d.name); } )
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[0]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth/2 + ", 0) ";
            })
            .attr("width", that._cfg.intervalwidth)
            .attr("height", function(d, i) {
                return that.valtop(d, d.interval[1]) - that.valtop(d, d.interval[0]);
            })
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");

                d3.select(this).moveToFront();
            })
            .on('mouseout', function(){
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
                d3.select(this).moveToBack();
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html("[" + d.interval[0].toPrecision(4) + ', ' + d.interval[1].toPrecision(4) +']')
                    // .html("[" + d.interval[0].toPrecision(4) + ', ' + d.interval[1].toPrecision(4) +']')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            });

        // update mininterval rectangles
        axes.select(".rs_miniv")
            .attr("class", function(d, i) { return "rs_miniv rs_miniv-"+that.replAxisname(d.name); } )
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[0]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth + ", 0) ";
            });

        // create mininterval rectangles
        axisenter.append("rect")
            .attr("class", function(d, i) { return "rs_miniv rs_miniv-"+that.replAxisname(d.name); } )
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[0]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth + ", 0) ";
            })
            .attr("fill", 'grey')
            .style("fill-opacity", 1)
            .attr("width", 2*that._cfg.intervalwidth)
            .attr("height", 5)
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mouseout', function(d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html("[" + d.interval[0].toPrecision(4) + ', ' + d.interval[1].toPrecision(4) +']')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .call(d3.behavior.drag()
                            .origin(Object)
                            .on("drag", function(d, i) {
                                var data = that.dragmove(d, i);

                                var l = that.valtop(d, data[2]);

                                // the position of the miniv rect is bound to the axis minimum on the lower side and the
                                // position of the maxiv rect on the upper side
                                var dragTarget = d3.select(this),
                                    miny = that.valtop(d, that._cfg.minValues[d.name]),
                                    maxy = that._svgContainer.select(".rs_maxiv-"+that.replAxisname(d.name)).attr('y');

                                dragTarget
                                    .attr("y", function(d, i){
                                        return Math.min(maxy, Math.max(miny, l));
                                    });

                                // the y coord of the interval bar is bound by the limits of the axis and the position
                                // of the maxiv rect
                                var inty = Math.min(l, dragTarget.attr("y"));

                                // update actual interval
                                that._svgContainer.select(".rs_iv-"+that.replAxisname(d.name))
                                    .attr("y", function(d, i){
                                        return l;
                                    })
                                    .attr("height", function(d, i){
                                        return maxy - inty;
                                    });

                                // update upper interval of axis
                                d.interval[0] = data[2];
                            })
                            .on('dragend', function(d, i) {

                                var _this = this;
                                that.dragend(d, i, _this, that);
                            })
            );

        // update maxinterval rectangles
        axes.select(".rs_maxiv")
            .attr("class", function(d, i) { return "rs_maxiv rs_maxiv-"+that.replAxisname(d.name); } )
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[1]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth + ", 0) ";
            });


        // create maxinterval rectangles
        axisenter.append("rect")
            .attr("class", function(d, i) { return "rs_maxiv rs_maxiv-"+that.replAxisname(d.name); })
            .attr("x", function(d, i){return 0;})
            .attr("y", function(d,i){
                return that.valtop(d, d.interval[1]);
            })
            .attr("transform", function(d, i){
                return "rotate(" + that.angledeg(i) + ", " + 0 + ", " + 0 +") translate(-" + that._cfg.intervalwidth + ", 0) ";
            })
            .attr("width", 2*that._cfg.intervalwidth)
            .attr("height", 5)
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mouseout', function(d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html("[" + d.interval[0].toPrecision(4) + ', ' + d.interval[1].toPrecision(4) +']')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .call(d3.behavior.drag()
                            .origin(Object)
                            .on("drag", function(d, i) {
                                var data = that.dragmove(d, i);

                                // initial length of the interval
                                var l = that.valtop(d, data[2]);

                                // the position of the maxiv rect is bound to the axis maximum on the upper side and the
                                // position of the miniv rect on the lower side
                                var dragTarget = d3.select(this),
                                    miny = that._svgContainer.select(".rs_miniv-"+that.replAxisname(d.name)).attr('y'),
                                    maxy = that.valtop(d, that._cfg.maxValues[d.name]);

                                dragTarget
                                    .attr("y", function(d, i){
                                        return Math.min(maxy, Math.max(miny, l));
                                    });

                                // the y coord of the interval bar is bound by the limits of the axis and the position
                                // of the miniv rect
                                var inty = Math.min(l, dragTarget.attr("y"));

                                // update actual interval
                                that._svgContainer.select(".rs_iv-"+that.replAxisname(d.name))
                                    .attr("height", function(d, i){
                                        return (inty) - miny;
                                    });

                                // update upper interval of axis
                                d.interval[1] = data[2];
                            })
                            .on('dragend', function(d, i) {
                                var _this = this;
                                that.dragend(d, i, _this, that);
                            })
            );

        /////////////////////////////////////////////////////////
        ///////////// Draw the radar chart blobs ////////////////
        /////////////////////////////////////////////////////////

        var data = [];
        var datasetnames = Object.keys(this._data);
        for (var name = 0; name < datasetnames.length; name++) {
            var tmp = [];
            for (var v=this._allAxis.length-1; v >= 0; v--) {
                tmp.push([datasetnames[name], that._data[datasetnames[name]][v], this._allAxis[v]]);
            }
            data.push(tmp);
        }

        //Create a wrapper for the blobs
        var blobwrapper = this._svgContainer.selectAll(".rs_datawrapper").data(data);

        var blobwrapperenter = blobwrapper
            .enter()
            .append("g")
            .attr("class", "rs_datawrapper");

        // append the polygon areas
        blobwrapperenter
            .append("path")
            .attr("class", function(d,i) { return "rs_area rs_area-" + that.replAxisname(d[0][0]); })
            .attr("d", function(d,i) { return that.radarline(d); })
            .style("fill", function(d,i) { return that._cfg.color(i); })
            .style("fill-opacity", this._cfg.opacityArea)
            .on('mouseover', function (d,i){
                //Dim all blobs
                that._svgContainer.selectAll(".rs_area")
                    .transition().duration(200)
                    .style("fill-opacity", 0.1);
                //Bring back the hovered over blob
                d3.select(this)
                    .transition().duration(200)
                    .style("fill-opacity", 0.7);
            })
            .on('mouseout', function(){
                //Bring back all blobs
                that._svgContainer.selectAll(".rs_area")
                    .transition().duration(200)
                    .style("fill-opacity", that._cfg.opacityArea);
            });

        // update the polygon areas
        blobwrapper.select(".rs_area")
            .attr("d", function(d,i) { return that.radarline(d); })
            .style("fill", function(d,i) { return that._cfg.color(i); })
            .style("fill-opacity", this._cfg.opacityArea);

        // append the area outlines
        blobwrapperenter
            .append("path")
            .attr("class", "rs_stroke")
            .attr("d", function(d,i) { return that.radarline(d); })
            .style("stroke-width", this._cfg.strokeWidth + "px")
            .style("stroke", function(d,i) { return that._cfg.color(i); })
            .style("filter" , "url(#glow" + this._id + ")");

        // update the area outlines
        blobwrapper.select(".rs_stroke")
            .attr("d", function(d,i) { return that.radarline(d); })
            .style("stroke-width", this._cfg.strokeWidth + "px")
            .style("stroke", function(d,i) { return that._cfg.color(i); });

        // append the circles
        blobwrapper.selectAll(".rs_datapoint")
            .data(function(d) { return d; })
            .enter()
            .append("circle")
            .attr("class", "rs_datapoint")
            .attr("r", this._cfg.dotRadius)
            .attr("cx", function(d){ return that.valtop(d[2], d[1]) * Math.cos(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2); })
            .attr("cy", function(d){ return that.valtop(d[2], d[1]) * (-Math.sin(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2)); })
            .style("fill", function(d,i,j) { return that._cfg.color(j); })
            .style("fill-opacity", 0.8);

        // update the circles
        blobwrapper.selectAll(".rs_datapoint")
            .attr("r", this._cfg.dotRadius)
            .attr("cx", function(d){ return that.valtop(d[2], d[1]) * Math.cos(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2); })
            .attr("cy", function(d){ return that.valtop(d[2], d[1]) * (-Math.sin(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2)); })
            .style("fill", function(d,i,j) { return that._cfg.color(j); });

        blobwrapper.exit().remove();

        /////////////////////////////////////////////////////////
        //////// Append invisible circles for tooltip ///////////
        /////////////////////////////////////////////////////////

        //Append a set of invisible circles on top for the mouseover pop-up
        // we need to determine the axes index differently here because it is not the index i from the dataset because
        // of the different data structure. We therefore determine it by retrieving the index of the axis from
        // this._allAxis
        var blobcirclewrapper = this._svgContainer.selectAll(".rs_invdatapointwrapper").data(data);

        blobcirclewrapper
            .enter().append("g")
            .attr("class", "rs_invdatapointwrapper");

        blobcirclewrapper.selectAll(".rs_invdatapoint")
            .data(function(d,i) { return d; })
            .enter()
            .append("circle")
            .attr("class", "rs_invdatapoint")
            .attr("r", this._cfg.dotRadius*1.5)
            .attr("cx", function(d,i){ return that.valtop(d[2], d[1]) * Math.cos(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2); })
            .attr("cy", function(d,i){ return that.valtop(d[2], d[1]) * (-Math.sin(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2)); })
            .style("fill", 'none')
            .style("pointer-events", "all")
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                    that._tooltip
                        .transition(200)
                        .style("display", "block");
            })
            .on('mouseout', function(d){
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);

                that._tooltip
                    .html(that.Format(d[2].unit, isNaN(d[1]) ? 0 : d[1]))
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");

            })
            .call(d3.behavior.drag()
                .origin(Object)
                .on("drag", function(d) {
                    // d is an array [datasetname, value, axis], so to get the correct dragmove values we need to
                    // pass it the correct index of the axis
                    var movedata = that.dragmove(d, that._allAxis.indexOf(d[2], 0));

                    //Bound the drag behavior to the max and min of the axis, not by pixels but by value calc (easier)
                    var dragTarget = d3.select(this);
                    dragTarget
                        .attr("cx", function(){ return that.valtop(d, movedata[2]) * Math.cos(that._cfg.angleslice*that._allAxis.indexOf(d, 0) + Math.PI/2); })
                        .attr("cy", function(){ return that.valtop(d, movedata[2]) * (-Math.sin(that._cfg.angleslice*that._allAxis.indexOf(d, 0) + Math.PI/2)); });

                    //Updating the data of the circle with the new value
                    that._data[d[0]][that._allAxis.indexOf(d[2], 0)] = movedata[2];
                    that.update();
                })
                .on('dragend', function(d, i) {
                    var _this = this;
                    that.dragend(d, that._allAxis.indexOf(d[2], 0), _this, that);
                })
            );

        blobcirclewrapper.selectAll(".rs_invdatapoint")
            .attr("r", this._cfg.dotRadius*1.5)
            .attr("cx", function(d,i){ return that.valtop(d[2], d[1]) * Math.cos(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2); })
            .attr("cy", function(d,i){ return that.valtop(d[2], d[1]) * (-Math.sin(that._cfg.angleslice*that._allAxis.indexOf(d[2]) + Math.PI/2)); })
            .style("pointer-events", "all");

        blobcirclewrapper.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadarSmoothed', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_rs_.RadarSmoothed( parent, properties);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'retrievesvg', 'updateAxis', 'addAxis', 'remAxis'],
    events: [ 'Selection' ]

} );