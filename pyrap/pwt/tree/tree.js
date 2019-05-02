pwt_tree = {};

pwt_tree.Tree = function( parent, options) {

    this._parentDIV =  this.createElement(parent);
    this._parent = parent;

    this._tooltip = d3.select(this._parentDIV).append("div")
            .attr('class', 'treetooltip')
            .style('z-index', 1000000);

    this._cfg = {
        TranslateX: 200,
        TranslateY: 10,
        duration: 750,
        i: 0,
        w: 900,
        h: 600,
        radius: 5
    };

    this._tree = d3.layout.tree().size([this._cfg.w, this._cfg.h]);
    this._data = {};
    this._nodes = [];
    this._links = [];

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.tree');

    this._initialized = false;

    var that = this;

    this.onresize = function () {
        that.setBounds( that._parent.getClientArea() )
    };

    rap.on( "render", function() {
        if( !that._initialized) {
            that.initialize( that, parent );
            that._initialized = true;
        }
        that.update({});
    } );
    this._parent.addListener( "Resize", this.onresize);
};

pwt_tree.Tree.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'tree')
                .attr("transform", "translate(" + this._cfg.TranslateX + "," + this._cfg.TranslateY + ")");
            this._svgContainer = this._svg.select('g.tree');
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
        if (typeof args[2] != 'undefined' && typeof args[3] != 'undefined' ) {
            this._cfg.w = Math.min(args[2],args[3]) - 100;
            this._cfg.h = this._cfg.w;
        }
        this.update(this._data);
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    destroy: function() {
        var element = this._parentDIV;
        if ( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
        this._parent.removeListener( "Resize", this.onresize);
    },

    setWidth: function( width ) {
        this._parentDIV.style.width = width + "px";
        this._cfg.w = width;
        this.update(this._data);
    },

    setHeight: function( height ) {
        this._parentDIV.style.height = height + "px";
        this._cfg.h = height;
        this.update(this._data);
    },

    /**
     * updates data options
     */
    setData : function ( data ) {
        // make sure to always re-render when received new data
        // TODO: find better way

        function collapse(d) {
            if (d.children) {
                d._children = d.children;
                d._children.forEach(collapse);
                d.children = null;
            }
        }

        this._data = data;

        if (this._data.children) {
            // clear old data
            this._data.x0 = this._cfg.h / 2;
            this._data.y0 = 0;

            this._data.children.forEach(collapse);
        }
        this.update(this._data);
        rap._.notify('render');
    },

    /**
     * Toggle children on click
     */
    click : function( d, that ) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else {
            d.children = d._children;
            d._children = null;
        }
        that.update(d);
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, this._svg.node().outerHTML );
    },

    diagonal : function(x) {
        return d3.svg.diagonal()
            .projection(function(d) {
                return [d.y, d.x];
            })(x);
    },

    /**
     * redraws the tree with the updated datapoints (expects a dictionary of
     * the form {"name":"random name1",
     *           "children":[
     *              {
     *              "name":"random name2",
     *              "url":"https://www.google.com",
     *              "children":[...]
     *              },
     *              ...
     *           ]
     *           }
     * )
     */
    update : function (source) {

        // no update before graph has been initialized
        if (!this._initialized) { rap._.notify('render'); }
        if (Object.keys(source).length === 0) { return; }

        var that = this;

        // resize tree
        this._tree
            .size([this._cfg.w, this._cfg.h]);

        // Compute the new tree layout.
        this._nodes = this._tree.nodes(this._data).reverse();
        this._links = this._tree.links(this._nodes);

        // Normalize for fixed-depth.
        this._nodes.forEach(function(d) { d.y = d.depth * 180; });

        // Update the nodes…
        var node = this._svgContainer.selectAll("g.tree_node")
            .data(this._nodes, function(d) { return d.id || (d.id = ++that._cfg.i); });

        // Enter any new nodes at the parent's previous position.
        var nodeenter = node
            .enter()
            .append("g")
            .attr("class", "tree_node")
            .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
            .on("click", function(d, i) {
                that.click(d, that);
            })
            .on("mouseover", function(d) {
                that._tooltip
                    .transition(200)
                    .style('display', 'block');
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.nodetooltip)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        nodeenter
            .append("circle")
            .attr("r", 1e-6)
            .style("fill", function(d) { return (typeof d._children  !== 'undefined' && d._children.length > 0) ? d.highlight ? "green" : "steelblue" : "white"; })
            .style("stroke", function(d) { return d.highlight ? "green" : "steelblue"; });

        nodeenter
            .append("svg:a")
            .attr("target", "E2B")
            .attr("href", function(d) { return d.url; })
            .append("text")
            .attr("x", function(d) { return d.children || d._children ? -10 : 10; })
            .attr("dy", "1.2em")
            .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
            .text(function(d) { return d.shownodetext ? d.nodetext : ''; })
            .style("fill-opacity", 1e-6);

        // Transition nodes to their new position.
        var nodeupdate = node
            .transition()
            .duration(this._cfg.duration)
            .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

        nodeupdate
            .select("circle")
            .attr("r", this._cfg.radius)
            .style("fill", function(d) { return d._children  && d._children.length > 0 ? d.highlight ? "green" : "steelblue" : "white"; });

        nodeupdate
            .select("text")
            .style("fill-opacity", 1);

        // Transition exiting nodes to the parent's new position.
        var nodeexit = node
            .exit()
            .transition()
            .duration(this._cfg.duration)
            .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
            .remove();

        nodeexit
            .select("circle")
            .attr("r", 1e-6);

        nodeexit
            .select("text")
            .style("fill-opacity", 1e-6);

        var edge = this._svgContainer.selectAll("g.tree_edge")
            .data(this._links, function(d) { return d.target.id; });

        // Enter any new linktexts at the parent's previous position.
        var edgeenter = edge
            .enter()
            .append("g")
            .attr("class", "tree_edge");

          // Enter any new links at the parent's previous position.
        edgeenter
            .append("path")
            .attr("class", "tree_link")
            .attr("id", function(d) { return d.source.nodetext + '-' + d.target.nodetext; })
            .attr("d", function(d) {
                var o = {x: source.x0, y: source.y0};
                return that.diagonal({source: o, target: o});
            });

        edgeenter
            .append("text")
            .style("font-size", "15px")
            .append("textPath")
            .attr("href", function(d) { return '#' + d.source.nodetext + '-' + d.target.nodetext; })
            .style('text-anchor', "middle")
            .attr("startOffset", "50%")
            .text(function(d) { return d.target.edgetext; })
            .on("mouseover", function() {
                that._tooltip
                    .transition(200)
                    .style('display', 'block');
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.target.edgetooltip)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function() {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        edgeenter
            .append("use")
            .attr("href", function(d) { return '#' + d.source.nodetext + '-' + d.target.nodetext; })
            .style("stroke", "black")
            .style("fill", "none");

          // Transition links to their new position.
        var edgeupdate = edge
            .transition()
            .duration(this._cfg.duration);

        edgeupdate
            .selectAll('path')
            .attr("d", that.diagonal)
            .style('stroke', function(d) { return d.target.highlight ? "green" : "steelblue"; });

        edgeupdate
            .select("text")
            .style("fill-opacity", 1);

        var edgeexit = edge
            .exit()
            .transition()
            .duration(this._cfg.duration)
            .remove();

        // Transition exiting nodes to the parent's new position.
        edgeexit
            .select('path')
            .attr("d", function(d) {
                var o = {x: source.x, y: source.y};
                return that.diagonal({source: o, target: o});
            });

        // Transition exiting nodes to the parent's new position.
        edgeexit
            .select(".treelink")
            .transition()
            .duration(this._cfg.duration)
            .attr("d", function(d) {
                var o = {x: source.x, y: source.y};
                return that.diagonal({source: o, target: o});
            }).remove();

        edgeexit
            .select("text")
            .style("fill-opacity", 1e-6);

        edgeexit
            .select("use")
            .remove();

        // Stash the old positions for transition.
        this._nodes.forEach(function(d) {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Tree', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_tree.Tree( parent, properties);
  },

  destructor: 'destroy',
  properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
  methods : [ 'retrievesvg'],
  events: [ 'Selection' ]

} );