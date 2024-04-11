pwt_tol = {};

pwt_tol.ToL = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3v6.select(this._parentDIV).append("div")
        .attr('class', 'toltooltip')
        .style('z-index', 1000000);

    this._svg = d3v6.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.tol');
    this._tollegend = this._svg.select('g.tol_legend');

    this._cfg = {
        width: 800,
        height: 800,
        glow: false,
        fontcolor: null,
        bgcolor: null,
        mode: null,
        trans: d3v6.transition().duration(750),
        showlen: false
    };
    this._curX = this._cfg.width / 2;
    this._curY = this._cfg.height / 2;

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

pwt_tol.ToL.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%");

            this._svg
                .append('g')
                .attr('class', 'tol_legend')
                .attr('transform', 'translate('+ -this._cfg.width/2 +',' + -this._cfg.width/2 + ')')// move legend svg to the top right corner
            this._tollegend = this._svg.select('g.tol_legend');

            this._svg
                .append('g')
                .attr('class', 'names');
            this._names = this._svg.select('g.names');

            this._svg
                .append('g')
                .attr('class', 'linkext')
                  .attr("fill", "none")
                  .attr("stroke", "#000")
                  .attr("stroke-opacity", 0.25);
            this._linkexts = this._svg.select('g.linkext');

            this._svg
                .append('g')
                .attr('class', 'links')
                .attr("fill", "none")
                .attr("stroke", "#000")
            this._links = this._svg.select('g.links');
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

        if (typeof args[2] !== 'undefined' && typeof args[3] !== 'undefined' ) {
            var oldwidth = this._cfg.width;
            var oldheight = this._cfg.height;
            this._cfg.width = Math.min(args[2],args[3]);
            this._cfg.height = this._cfg.width;
            this._curX += (this._cfg.width - oldwidth) / 2;
            this._curY += (this._cfg.height - oldheight) / 2;
        }
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
     * Compute the maximum cumulative length of any node in the tree.
     * @param d
     * @returns {*}
     */
    // maxLength: function(d) {
    //     console.log();
    //     return d.data.length + (d.children ? d3v6.max(d.children, this.maxLength) : 0);
    // },
    //
    // /**
    //  * Set the radius of each node by recursively summing and scaling the distance from the root.
    //  */
    // setRadius: function (d, y0, k) {
    //     console.log('setting radius', d, y0, k, (y0 += d.data.length) * k);
    //     d.radius = (y0 += d.data.length) * k;
    //     if (d.children) d.children.forEach(d => this.setRadius(d, y0, k));
    // },

    /**
     * Set the color of each node by recursively inheriting.
     * @param d
     */
    // setColor: function(that, d) {
    //     console.log(d);
    //   var name = d.data.name;
    //   d.color = that._color.domain().indexOf(name) >= 0 ? that._color(name) : d.parent ? d.parent.color : null;
    //   if (d.children) d.children.forEach(this.setColor);
    // },

    /**
     *
     * @param d
     * @returns {*}
     */
    // linkVariable: function(d) {
    //   return this.linkStep(d.source.x, d.source.radius, d.target.x, d.target.radius);
    // },

    /**
     *
     * @param d
     * @returns {*}
     */
    // linkConstant: function(d) {
    //   return this.linkStep(d.source.x, d.source.y, d.target.x, d.target.y);
    // },

    /**
     *
     * @param d
     * @returns {*}
     */
    // linkExtensionVariable: function(d) {
    //   return this.linkStep(d.target.x, d.target.radius, d.target.x, this._innerRadius);
    // },

    /**
     *
     * @param showlen
     * @returns {*}
     */
    setShowlen: function(showlen) {
        this._cfg.showlen = showlen;
        this.update();
    },

    /**
     *
     * @param startAngle
     * @param startRadius
     * @param endAngle
     * @param endRadius
     * @returns {string}
     */
    linkStep: function (startAngle, startRadius, endAngle, endRadius) {
      const c0 = Math.cos(startAngle = (startAngle - 90) / 180 * Math.PI);
      const s0 = Math.sin(startAngle);
      const c1 = Math.cos(endAngle = (endAngle - 90) / 180 * Math.PI);
      const s1 = Math.sin(endAngle);
      return "M" + startRadius * c0 + "," + startRadius * s0
          + (endAngle === startAngle ? "" : "A" + startRadius + "," + startRadius + " 0 0 " + (endAngle > startAngle ? 1 : 0) + " " + startRadius * c1 + "," + startRadius * s1)
          + "L" + endRadius * c1 + "," + endRadius * s1;
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
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, [this._svg.node().outerHTML, args.fname] );
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        // preprocess data
        this._data = data;
        this._dataloaded = true;
        this.update();
    },


    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {
        // no update before graph has been initialized
        if (!this._initialized) { return; }
        if (!this._dataloaded) { return; }

        var that = this;

        // put d3js code here
        var outerRadius = this._cfg.width / 2;
        var innerRadius = outerRadius - 170;

        this._cluster = d3v6.cluster()
            .size([360, innerRadius])
            .separation((a, b) => 1)

        this._color = d3v6.scaleOrdinal()
            .domain(["Bacteria", "Eukaryota", "Archaea"])
            .range(d3v6.schemeCategory10)

        var setColor = function(d) {
            var name = d.data.name;
            d.color = that._color.domain().indexOf(name) >= 0 ? that._color(name) : d.parent ? d.parent.color : null;
            if (d.children) d.children.forEach(setColor);
        };

        var maxLength = function(d) {
            console.log();
            return d.data.length + (d.children ? d3v6.max(d.children, maxLength) : 0);
        };

        var setRadius = function(d, y0, k) {
            console.log('setting radius', d, y0, k, (y0 += d.data.length) * k);
            d.radius = (y0 += d.data.length) * k;
            if (d.children) d.children.forEach(d => setRadius(d, y0, k));
        };

        this.linkExtensionConstant = function(d) {
            return that.linkStep(d.target.x, d.target.y, d.target.x, innerRadius);
        };

        this.linkExtensionVariable = function(d) {
            return that.linkStep(d.target.x, d.target.radius, d.target.x, innerRadius);
        };

        this.linkConstant = function(d) {
            return that.linkStep(d.source.x, d.source.y, d.target.x, d.target.y);
        };

        this.linkVariable = function(d) {
            return that.linkStep(d.source.x, d.source.radius, d.target.x, d.target.radius);
        };

        this._root = d3v6.hierarchy(this._data, d => d.branchset)
            .sum(d => d.branchset ? 0 : 1)
            .sort((a, b) => (a.value - b.value) || d3v6.ascending(a.data.length, b.data.length));

        this._cluster(this._root);
        setRadius(this._root, this._root.data.length = 0, innerRadius / maxLength(this._root));
        setColor(this._root);

        // Update the view
        this._svg
            .attr("viewBox", [-outerRadius, -outerRadius, this._cfg.width, this._cfg.width])

        // Generate/update legend
        var enterlegendelements = function(enter) {
            enter.append('g')
                .attr("transform", (d, i) => `translate(${-outerRadius},${-outerRadius + i * 20})`)
            .call(g =>
                g.append('rect')
                    .attr("width", 18)
                    .attr("height", 18)
                    .attr("fill", d => that._color(d))
            )
            .call(g =>
                g.append('text')
                    .attr("x", 24)
                    .attr("y", 9)
                    .attr("dy", "0.35em")
                    .text(d => d)
                  .raise()
            )
        };

        var updatelegendelements = function(update) {
            update
                .attr("transform", (d, i) => `translate(${-outerRadius},${-outerRadius + i * 20})`)
        };

        var exitlegendelements = function(exit) {
            exit
                .call(g =>
                    g.transition().duration(750)
                        .attr('transform', (d,i) => `translate(${ 10 },${ 350 })`)
                        .style('opacity', 0)
                    .remove()
                )
        };

        this._tollegend.selectAll('g')
            .data(this._color.domain(), d => d)
            .join(
                enter => enterlegendelements(enter),
                update => updatelegendelements(update),
                exit => exitlegendelements(exit)
            );

        var mouseovered = function(active) {
            return function(event, d) {
                d3v6.select(this).classed("label--active", active);
                d3v6.select(d.linkExtensionNode).classed("link-extension--active", active).raise();
                do d3v6.select(d.linkNode).classed("link--active", active).raise();
                while (d = d.parent);
            };
        }

        // generate text elements
        this._names.selectAll("text")
            .data(this._root.leaves())
            .join("text")
                .attr("dy", ".31em")
                .attr("transform", d => `rotate(${d.x - 90}) translate(${innerRadius + 4},0)${d.x < 180 ? "" : " rotate(180)"}`)
                .attr("text-anchor", d => d.x < 180 ? "start" : "end")
                .text(d => d.data.name.replace(/_/g, " "))
                .on("mouseover", mouseovered(true))
                .on("mouseout", mouseovered(false));

        // generate outer paths
        this._linkexts.selectAll("path")
            .data(this._root.links().filter(d => !d.target.children))
            .join("path")
                .each(function(d) { d.target.linkExtensionNode = this; })
                // .transition(d3v6.transition().duration(750))
                .attr("d", this._cfg.showlen ? this.linkExtensionVariable : this.linkExtensionConstant);

        // generate inner paths
        this._links.selectAll("path")
            .data(this._root.links())
            .join("path")
                .each(function(d) { d.target.linkNode = this; })
                // .transition(d3v6.transition().duration(750))
                .attr("d", that._cfg.showlen ? that.linkVariable : that.linkConstant)
                .attr("stroke", d => d.target.color)
                .on('mouseover', function(d) {
                    d3v6.select(this).style("cursor", "pointer");

                    that._tooltip
                        .transition(200)
                        .style("display", "block");
                })
                .on('mouseout', function(d){
                    d3v6.select(this).style("cursor", "default");
                    that._tooltip
                        .transition(200)
                        .style("display", "none");
                })
                .on('mousemove', function(event, d) {
                    var newX = (event.pageX + 20);
                    var newY = (event.pageY - 20);

                    that._tooltip
                        .html(d.source.data.name + '-->' + d.target.data.name)
                        .style("left", (newX) + "px")
                        .style("top", (newY) + "px");
                });


        // const t = d3v6.transition().duration(750);

        // this._linkexts.transition(t).attr("d", this._cfg.showlen ? this.linkExtensionVariable : this.linkExtensionConstant);
        // this._links.transition(t).attr("d", this._cfg.showlen ? this.linkVariable : this.linkConstant);
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.ToL', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_tol.ToL( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds', 'showlen'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );