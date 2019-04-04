pwt_radar_smoothed = {};

pwt_radar_smoothed.RadarSmoothed = function( parent, audio ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'radar_smoothedtooltip')
        .style('z-index', 1000000);

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.radar_smoothed');

    this._cfg = {
        w: 800,
        h: 600,
        radius: 100,
        angleslice: Math.PI * 2/3,
        factorLegend: .85,
        top: 100,
        right: 100,
        bottom: 110,
        left: 100,
        maxValue: 0.5,          //What is the value that the biggest circle will represent
        levels: 5,              //How many levels or inner circles should there be drawn
        labelFactor: 1.25,   	//How much farther than the radius of the outer circle should the labels be placed
        wrapWidth: 60, 		    //The number of pixels after which a label needs to be given a new line
        opacityArea: 0.35, 	    //The opacity of the area of the blob
        dotRadius: 4, 			//The size of the colored circles of each blog
        opacityCircles: 0.1, 	//The opacity of the circles of each blob
        strokeWidth: 2, 		//The width of the stroke around each blob
        roundStrokes: true,	    //If true the area and stroke will follow a round path (cardinal-closed)
        color: d3.scale.ordinal(),
        defaultformat: d3.format('%'),
        maxValues: {},          // mapping axis name to max value
        minValues: {}           // mapping axis name to min value
	};

    this._allAxis = [];
    this._total = this._allAxis.length;

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

pwt_radar_smoothed.RadarSmoothed.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'radar_smoothed')
                .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ")");
            this._svgContainer = this._svg.select('g.radar_smoothed');
        }

        // Glow filter
        this._defs = this._svgContainer
            .append('defs');

        this._filter = this._defs
            .append('filter')
            .attr('id','glow');

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
            this._cfg.w = Math.max(400, args[2] - this._cfg.left - this._cfg.right);
            this._cfg.h = Math.max(300, args[3] - this._cfg.top - this._cfg.bottom);
        }

        this._svgContainer
            .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ")");

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
        // preprocess data
        this._data = data;
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
            return (value >= 0.1 ? d3.format(".2f")(value) : d3.format(".2e")(value)) + unit;
		}
    },

    /**
     * updates an axis of the radar chart
     */
    updateAxis : function ( data ) {
        for (var x = 0; x < this._allAxis.length; x++) {
            if (this._allAxis[x].name == data.axis.name) {
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
        this._total = this._allAxis.length;

        // add min and max values for the new axis
        this._cfg.minValues[axis.name] = (typeof axis.limits[0]) !== 'undefined' ? axis.limits[0]: 0;
        this._cfg.maxValues[axis.name] = (typeof axis.limits[1]) !== 'undefined' ? axis.limits[1]: 100;

        // update
        this.update();
    },


    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        // update translation of main group
        this._svgContainer
                .attr("transform", "translate(" + (this._cfg.w/2 + this._cfg.left) + "," + (this._cfg.h/2 + this._cfg.top) + ")");

        this._cfg.color
            .range(["#EDC951","#CC333F","#00A0B0"]);

        //If the supplied maxValue is smaller than the actual one, replace by the max in the data
        var maxValue = Math.max(this._cfg.maxValue, d3.max(this._data, function(i){return d3.max(i.map(function(o){return o.value;}))}));

        this._cfg.radius = Math.min(this._cfg.w/2, this._cfg.h/2);	//Radius of the outermost circle
        this._cfg.angleslice = Math.PI * 2 / this._total;		                //The width in radians of each "slice"

        //Scale for the radius
        var rScale = d3.scale.linear()
            .range([0, this._cfg.radius])
            .domain([0, maxValue]);


        /////////////////////////////////////////////////////////
        /////////////// Draw the Circular grid //////////////////
        /////////////////////////////////////////////////////////
        var axisgrid = this._svgContainer.selectAll('g.axisWrapper').data([0]);

        var axisgridenter = axisgrid
            .enter()
            .append('g')
            .attr('class', 'axisWrapper');

        axisgrid.exit().remove();

        //Draw the background circles
        var axislevels = axisgrid.selectAll(".radar_smoothedlevels").data(d3.range(1,(this._cfg.levels+1)).reverse());

        axislevels
           .enter()
            .append("circle")
            .attr("class", "radar_smoothedlevels")
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;})
            .style("fill-opacity", this._cfg.opacityCircles)
            .style("filter" , "url(#glow)");

        axislevels
            .attr("r", function(d, i){return that._cfg.radius/that._cfg.levels*d;})
            .style("fill-opacity", this._cfg.opacityCircles);

        axislevels.exit().remove();


        /////////////////////////////////////////////////////////
        //////////////////// Draw the axes //////////////////////
        /////////////////////////////////////////////////////////

        //Create the straight lines radiating outward from the center
        var axes = axisgrid.selectAll("g.radar_smoothedaxis").data(this._allAxis);

        var axisenter = axes
            .enter()
            .append('g')
            .attr('class', 'radar_smoothedaxis');

        // append the lines
        axisenter
            .append("line")
            .attr("class", "radar_smoothedline")
            .attr("x1", 0)
            .attr("y1", 0)
            .attr("x2", function(d, i){ return rScale(maxValue*1.1) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("y2", function(d, i){ return rScale(maxValue*1.1) * Math.sin(that._cfg.angleslice*i - Math.PI/2); });

        // update the lines
        axes.select(".radar_smoothedline")
            .attr("x2", function(d, i){ return rScale(maxValue*1.1) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("y2", function(d, i){ return rScale(maxValue*1.1) * Math.sin(that._cfg.angleslice*i - Math.PI/2); });

        // append the axis labels
        axisenter
            .append("text")
            .attr("class", "radar_smoothedlegend")
            .attr("text-anchor", "middle")
            .attr("dy", "0.35em")
            .attr("x", function(d, i){ return rScale(maxValue * that._cfg.labelFactor) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("y", function(d, i){ return rScale(maxValue * that._cfg.labelFactor) * Math.sin(that._cfg.angleslice*i - Math.PI/2); })
            .text(function(d){return d.name})
            .call(wrap, this._cfg.wrapWidth);

        // update the labels
        axes.select(".radar_smoothedlegend")
            .attr("x", function(d, i){ return rScale(maxValue * that._cfg.labelFactor) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("y", function(d, i){ return rScale(maxValue * that._cfg.labelFactor) * Math.sin(that._cfg.angleslice*i - Math.PI/2); })
            .text(function(d){return d.name})
            .call(wrap, this._cfg.wrapWidth);

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
        var axislabels = axes.selectAll(".radar_smoothedaxisLabel").data(newaxis);

        axislabels
           .enter()
            .append("text")
            .attr("class", "radar_smoothedaxisLabel")
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


        axes.exit().remove();

        /////////////////////////////////////////////////////////
        ///////////// Draw the radar chart blobs ////////////////
        /////////////////////////////////////////////////////////

        //The radial line function
        var radarLine = d3.svg.line.radial()
            .interpolate("linear-closed")
            .radius(function(d) { return rScale(d.value); })
            .angle(function(d,i) {	return i*that._cfg.angleslice; });

        if(this._cfg.roundStrokes) {
            radarLine.interpolate("cardinal-closed");
        }

        //Create a wrapper for the blobs
        var blobwrapper = this._svgContainer.selectAll(".radarWrapper").data(this._data);

        var blobwrapperenter = blobwrapper
            .enter()
            .append("g")
            .attr("class", "radarWrapper");

        // append the polygon areas
        blobwrapperenter
            .append("path")
            .attr("class", "radarArea")
            .attr("d", function(d,i) { return radarLine(d); })
            .style("fill", function(d,i) { return that._cfg.color(i); })
            .style("fill-opacity", this._cfg.opacityArea)
            .on('mouseover', function (d,i){
                //Dim all blobs
                d3.selectAll(".radarArea")
                    .transition().duration(200)
                    .style("fill-opacity", 0.1);
                //Bring back the hovered over blob
                d3.select(this)
                    .transition().duration(200)
                    .style("fill-opacity", 0.7);
            })
            .on('mouseout', function(){
                //Bring back all blobs
                d3.selectAll(".radarArea")
                    .transition().duration(200)
                    .style("fill-opacity", that._cfg.opacityArea);
            });

        // update the polygon areas
        blobwrapper.select(".radarArea")
            .attr("d", function(d,i) { return radarLine(d); })
            .style("fill", function(d,i) { return that._cfg.color(i); })
            .style("fill-opacity", this._cfg.opacityArea);

        // append the area outlines
        blobwrapperenter.append("path")
            .attr("class", "radarStroke")
            .attr("d", function(d,i) { return radarLine(d); })
            .style("stroke-width", this._cfg.strokeWidth + "px")
            .style("stroke", function(d,i) { return that._cfg.color(i); })
            .style("filter" , "url(#glow)");

        // update the area outlines
        blobwrapper.select(".radarStroke")
            .attr("d", function(d,i) { return radarLine(d); })
            .style("stroke-width", this._cfg.strokeWidth + "px")
            .style("stroke", function(d,i) { return that._cfg.color(i); });

        // append the circles
        blobwrapper.selectAll(".radarCircle")
            .data(function(d,i) { return d; })
            .enter().append("circle")
            .attr("class", "radarCircle")
            .attr("r", this._cfg.dotRadius)
            .attr("cx", function(d,i){ return rScale(d.value) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("cy", function(d,i){ return rScale(d.value) * Math.sin(that._cfg.angleslice*i - Math.PI/2); })
            .style("fill", function(d,i,j) { return that._cfg.color(j); })
            .style("fill-opacity", 0.8);

        // update the circles
        blobwrapper.selectAll(".radarCircle")
            .attr("r", this._cfg.dotRadius)
            .attr("cx", function(d,i){ return rScale(d.value) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("cy", function(d,i){ return rScale(d.value) * Math.sin(that._cfg.angleslice*i - Math.PI/2); })
            .style("fill", function(d,i,j) { return that._cfg.color(j); });

        blobwrapper.exit().remove();

        /////////////////////////////////////////////////////////
        //////// Append invisible circles for tooltip ///////////
        /////////////////////////////////////////////////////////

        //Wrapper for the invisible circles on top
        var blobCircleWrapper = this._svgContainer.selectAll(".radarCircleWrapper")
            .data(this._data)
            .enter().append("g")
            .attr("class", "radarCircleWrapper");

        //Append a set of invisible circles on top for the mouseover pop-up
        blobCircleWrapper.selectAll(".radarInvisibleCircle")
            .data(function(d,i) { return d; })
            .enter().append("circle")
            .attr("class", "radarInvisibleCircle")
            .attr("r", this._cfg.dotRadius*1.5)
            .attr("cx", function(d,i){ return rScale(d.value) * Math.cos(that._cfg.angleslice*i - Math.PI/2); })
            .attr("cy", function(d,i){ return rScale(d.value) * Math.sin(that._cfg.angleslice*i - Math.PI/2); })
            .style("fill", "none")
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
                    .html(that._cfg.defaultformat(d.value))
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");

            });


        /////////////////////////////////////////////////////////
        /////////////////// Helper Function /////////////////////
        /////////////////////////////////////////////////////////

        //Taken from http://bl.ocks.org/mbostock/7555321
        //Wraps SVG text
        function wrap(text, width) {
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
        }//wrap
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadarSmoothed', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_radar_smoothed.RadarSmoothed( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'clear', 'retrievesvg', 'updateAxis', 'addAxis', 'remAxis'],
    events: [ 'Selection' ]

} );