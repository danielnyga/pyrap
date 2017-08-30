// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_cluster = {};

pwt_cluster.Cluster = function( parent, opts) {

    this._parentDIV = this.createElement(parent);
    this._p = parent;
    this._data = {};

    this._wwidth = window.innerWidth;
    this._wheight = window.innerHeight;
    var diameter = Math.min(this._wwidth, this._wheight),
        radius = diameter / 2,
        innerRadius = radius - 170;

    this._cluster = d3.layout.cluster()
        .separation(function(a, b) { return (a.parent == b.parent ? 1 : 5 ) }) // gap between elements: 1, between groups: 5
        .size([360, innerRadius])
        .sort(null)
        .value(function(d) { return d.size; });

    this._bundle = d3.layout.bundle();

    this._line = d3.svg.line.radial()
        .interpolate("bundle")
        .tension(.75)
        .radius(function(d) { return d.y; })
        .angle(function(d) { return d.x / 180 * Math.PI; });

    d3.select(self.frameElement).style("height", diameter + "px");

    this._svg = d3.select(this._parentDIV).append("svg");

    this._svgContainer = this._svg.select('g.cluster');

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

pwt_cluster.Cluster.prototype = {

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


        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'cluster')
                .attr("transform", "translate(" + (this._wwidth/2) + "," + (this._wheight/2) + ")");
            this._svgContainer = this._svg.select('g.cluster');
        }

        this.update();
    },

    createElement: function( parent ) {
        console.log('parent', parent);
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
        console.log('this id', this._rwtId);

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
        // clear data
        this.setData( {} );
    },


    /**
     * updates data options
     */
    setData : function ( data ) {
        this._data = data;
        this._nodes = this._cluster.nodes(this.nodeHierarchy(data));
        this._links = this.packageImports(this._nodes);
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

        var textTags = document.getElementsByTagName("text");
        var searchText = hl.name;
        var found;

        for (var i = 0; i < textTags.length; i++) {
            if (textTags[i].textContent == searchText) {
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

        this._svgContainer.selectAll(".node")
            .each(function(n) { n.target = n.source = false; });

        this._svgContainer.selectAll(".link")
            .classed("link--target", function(l) { if (l.target === d) return l.source.source = true; })
            .classed("link--source", function(l) { if (l.source === d) return l.target.target = true; })
            .filter(function(l) { return l.target === d || l.source === d; })
            .each(function() { this.parentNode.appendChild(this); });

        this._svgContainer.selectAll(".node")
            .classed("node--target", function(n) { return n.target; })
            .classed("node--source", function(n) { return n.source; });

        d3.select(_this)
            .style("fill", "steelblue")
            .attr("font-weight", 700);

        // split selections if different colors needed
        this._svgContainer.selectAll(".node--source, .node--target")
            .each(function(d) {
                d3.select(this)
                    .style("fill", "steelblue")
                    .attr("font-weight", 700);
            });

        // split selections if different colors needed
        this._svgContainer.selectAll(".link--source, .link--target")
            .each(function(d) {
                d3.select(this)
                    .style("stroke", "steelblue")
                    .style("stroke-opacity", 1)
                    .style("stroke-width", "2px");
            });
    },

    mouseout: function (d) {
        this._svgContainer.selectAll(".link")
            .classed("link--target", false)
            .classed("link--source", false)
            .style("fill", "none")
            .style("stroke-opacity", .2)
            .style("stroke-width", "2px");

        this._svgContainer.selectAll(".node")
            .classed("node--target", false)
            .classed("node--source", false)
            .style("fill", "#636363")
            .attr("font-weight", 300);

    },




    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        var links = this._svgContainer.selectAll(".link").data(this._bundle(this._links));

        links
            .each(function(d) { d.source = d[0], d.target = d[d.length - 1]; });

        links
            .enter()
            .append("path")
            .each(function(d) { d.source = d[0], d.target = d[d.length - 1]; })
            .attr("class", "link")
            .style("stroke", "steelblue")
            .style("stroke-opacity", .5)
            .style("fill", 'none')
            .attr("d", this._line);

        links.exit().remove();

        var nodes = this._svgContainer.selectAll(".node").data(this._nodes.filter(function(n) { return !n.children; }));

        nodes
            .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + (d.y + 8) + ",0)" + (d.x < 180 ? "" : "rotate(180)"); })
            .style("text-anchor", function(d) { return d.x < 180 ? "start" : "end"; })
            .text(function(d) { return d.key; });

        nodes
            .enter()
            .append("text")
            .attr("class", "node")
            .style("font-family", "Helvetica, Arial, sans-serif")
            .style("font-size", "9px")
            .attr("font-weight", 300)
            .style("fill", "#636363")
            .attr("dy", ".31em")
            .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + (d.y + 8) + ",0)" + (d.x < 180 ? "" : "rotate(180)"); })
            .style("text-anchor", function(d) { return d.x < 180 ? "start" : "end"; })
            .text(function(d) { return d.key; })
            .on('mouseover', function(d, i) {

                var _this = this;
                that.mouseover(d, _this);
            })
            .on('mouseout', function(d, i) {

                var _this = this;
                that.mouseout(d, _this);
            });

        nodes.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Cluster', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_cluster.Cluster( parent, properties.options);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height', 'data'],

  methods : [ 'updateData', 'clear', 'highlight'],

  events: [ 'Selection' ]

} );