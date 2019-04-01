// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_radialdendrogramm = {};

pwt_radialdendrogramm.RadialDendrogramm = function( parent) {

    this._parentDIV = this.createElement(parent);
    this._data = {};

    this._w = 800;
    this._h = 600;

    this._cluster = d3.layout.cluster()
        .separation(function(a, b) { return (a.parent === b.parent ? 1 : 5 ) }) // gap between elements: 1, between groups: 5
        .sort(null)
        .value(function(d) { return d.size; });

    this._bundle = d3.layout.bundle();
    this._line = d3.svg.line.radial()
        .interpolate("bundle")
        .tension(.75)
        .radius(function(d) { return d.y; })
        .angle(function(d) { return d.x / 180 * Math.PI; });

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.radialdendrogram');

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

pwt_radialdendrogramm.RadialDendrogramm.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'radialdendrogram')
                .attr("transform", "translate(" + (this._w/2) + "," + (this._h/2) + ")");
            this._svgContainer = this._svg.select('g.radialdendrogram');
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
        this._w = args[2] ? args[2] : 800;
        this._h = args[3] ? args[3] : 600;
        if (this._svgContainer.node() !== null ) {
            this._svgContainer
                .attr("transform", "translate(" + (this._w/2) + "," + (this._h/2) + ")");
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
     * Lazily construct the package hierarchy from class names.
     */
    nodeHierarchy: function( classes ) {
        var map = {};

        function find(name, data) {
            var node = map[name], i;
            if (!node) {
                node = map[name] = data || {name: name, children: []};
                if (name.length) {
                    // assumes node names to be of the form groupname.nodename
                    node.parent = find(name.substring(0, i = name.indexOf(".")));
                    node.parent.children.push(node);
                    node.key = name.substring(i = name.indexOf(".")+1, name.length);
                }
            }
            return node;
        }

        classes.forEach(function(d) {
            find(d.name, d);
        });

      return map[""];
    },

    /**
     * Return a list of imports for the given array of nodes.
     */
    packageImports: function( nodes ) {
        var map = {},
            imports = [];

        // Compute a map from name to node.
        nodes.forEach(function(d) {
            map[d.name] = d;
        });

        // For each import, construct a link from the source to target node.
        nodes.forEach(function(d) {
            if (d.imports) d.imports.forEach(function(i) {
                imports.push({source: map[d.name], target: map[i]});
            });
        });

        return imports;
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
        this._data = data;
        this._root = this.nodeHierarchy(data);
        this.update();
    },

    /**
     * updates data options
     */
    highlight : function ( hl ) {
        this.clearhighlight();

        function findnode( node ) {
            return node.key === hl.name;
        }

        el = this._nodes.filter(findnode);

        var textTags = this._svgContainer.selectAll(".radialdnode");
        var searchText = hl.name;
        var found;

        for (var i = 0; i < textTags.length; i++) {
            if (textTags[i].textContent === searchText) {
                found = textTags[i];
                break;
            }
        }
        this.mouseover(el[0], found);
    },

    /**
     * updates data options
     */
    clearhighlight : function ( ) {
        this.mouseout();
    },


    mouseover: function (d, _this) {

        // clear previous highlight
        this._svgContainer.selectAll(".radialdnode")
            .each(function(n) { n.target = n.source = false; });

        // mark the correct links for highlighting
        this._svgContainer.selectAll(".radialdlink")
            .classed("radialdlink--target", function(l) { if (l.target === d) return l.source.source = true; })
            .classed("radialdlink--source", function(l) { if (l.source === d) return l.target.target = true; })
            .filter(function(l) { return l.target === d || l.source === d; })
            .each(function() { this.parentNode.appendChild(this); });

        // mark the correkt nodes for highlighting
        this._svgContainer.selectAll(".radialdnode")
            .classed("radialdnode--target", function(n) { return n.target; })
            .classed("radialdnode--source", function(n) { return n.source; });

        d3.select(_this)
            .style("fill", "steelblue")
            .style("font-weight", "bold");

        // split selections if different colors needed
        this._svgContainer.selectAll(".radialdnode--source, .radialdnode--target")
            .each(function(d) {
                d3.select(this)
                    .style("fill", "steelblue")
                    .style("font-weight", "bold");
            });

        // split selections if different colors needed
        this._svgContainer.selectAll(".radialdlink--source, .radialdlink--target")
            .each(function(d) {
                d3.select(this)
                    .style("stroke-opacity", 1)
                    .style("stroke-width", "2px");
            });
    },

    mouseout: function (d) {
        this._svgContainer.selectAll(".radialdlink")
            .classed("radialdlink--target", false)
            .classed("radialdlink--source", false)
            .style("fill", "none")
            .style("stroke-opacity", .2)
            .style("stroke-width", "2px");

        this._svgContainer.selectAll(".radialdnode")
            .classed("radialdnode--target", false)
            .classed("radialdnode--source", false)
            .style("fill", "#636363")
            .style("font-weight", "normal");

    },

    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        this._radius = Math.min(this._w, this._h) / 2;
        this._innerradius = this._radius - 150;

        this._nodes = this._cluster
            .size([360, this._innerradius])
            .nodes(this._root);

        this._links = this.packageImports(this._nodes);

        var links = this._svgContainer.selectAll(".radialdlink").data(this._bundle(this._links));

        links
            .each(function(d) { d.source = d[0]; d.target = d[d.length - 1]; })
            .attr("d", this._line);

        links
            .enter()
            .append("path")
            .each(function(d) { d.source = d[0]; d.target = d[d.length - 1]; })
            .attr("class", "radialdlink")
            .style("stroke-opacity", .5)
            .style("fill", 'none')
            .attr("d", this._line);

        links.exit().remove();

        var nodes = this._svgContainer.selectAll(".radialdnode").data(this._nodes.filter(function(n) { return !n.children; }));

        nodes
            .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + (d.y + 8) + ",0)" + (d.x < 180 ? "" : "rotate(180)"); })
            .style("text-anchor", function(d) { return d.x < 180 ? "start" : "end"; })
            .text(function(d) { return d.key; });

        nodes
            .enter()
            .append("text")
            .attr("class", "radialdnode")
            .attr("dy", ".31em")
            .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + (d.y + 8) + ",0)" + (d.x < 180 ? "" : "rotate(180)"); })
            .style("text-anchor", function(d) { return d.x < 180 ? "start" : "end"; })
            .text(function(d) { return d.key; })
            .on('mouseover', function(d) {
                d3.select(this).style("cursor", "pointer");
                that.mouseover(d, this);
            })
            .on('mouseout', function(d, i) {
                d3.select(this).style("cursor", "default");
                that.mouseout(d, this);
            });

        nodes.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadialDendrogramm', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_radialdendrogramm.RadialDendrogramm( parent, properties.options);
  },

  destructor: 'destroy',
  properties: [ 'width', 'height', 'data', 'bounds'],
  methods : [ 'clear', 'highlight', 'retrievesvg'],
  events: [ 'Selection' ]

} );