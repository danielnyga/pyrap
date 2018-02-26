pwt_tree = {};

pwt_tree.Tree = function( parent, options) {

    var margin = {top: 10, right: 120, bottom: 10, left: 120};

    this._cfg = {
        TranslateX: margin.left,
        TranslateY: margin.top,
        duration: 750,
        i: 0,
        w: 960 - margin.right - margin.left,
        h: 800 - margin.top - margin.bottom
    };

    this._tree = d3.layout.tree().size([this._cfg.w, this._cfg.h]);
    this._diagonal = d3.svg.diagonal().projection(function(d) {
        return [d.y, d.x];
    });

    this._parentDIV = this.createElement(parent);
    this._data = {};

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g');

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

pwt_tree.Tree.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr("transform", "translate(" + this._cfg.TranslateX + "," + this._cfg.TranslateY + ")");
            this._svgContainer = this._svg.select('g');
        }

        this.update(this._data);
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
            this._cfg.w = Math.min(args[2],args[3]) - 100;
            this._cfg.h = this._cfg.w;
        }
        this._svgContainer
            .attr("transform", "translate(" + this._cfg.TranslateX + "," + this._cfg.TranslateY + ")");

        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
        this.update(this._data);
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
        // clear old data
        console.log('this._cfg.h', this._cfg.h);
        this._data = data;
        this._data.x0 = this._cfg.h / 2;
        this._data.y0 = 0;
        console.log(this._data);

        function collapse(d) {
            if(d.children) {
                d._children = d.children;
                d._children.forEach(collapse);
                d.children = null;
            }
        }
        this._data.children.forEach(collapse);
        this.update(this._data);
    },

    /**
     * Toggle children on click
     */
    click: function( d, that ) {
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
        // resize tree
        this._tree.size([this._cfg.w, this._cfg.h]);

        // no update before graph has been initialized
        if ( typeof source === 'undefined') { return; }
        var that = this;


        // Compute the new tree layout.
        var nodes = this._tree.nodes(this._data).reverse(),
            links = this._tree.links(nodes);

        // Normalize for fixed-depth.
        nodes.forEach(function(d) { d.y = d.depth * 180; });

        // Update the nodes…
        var node = this._svgContainer.selectAll("g.node")
            .data(nodes, function(d) { return d.id || (d.id = ++that._cfg.i); });

        // Enter any new nodes at the parent's previous position.
        var nodeEnter = node.enter().append("g")
            .attr("class", "node")
            .attr("transform", function(d) { return "translate(" + source.y0 + "," + source.x0 + ")"; })
            .on("click", function(d, i) {
                var _this = this;
                that.click(d, that);
            })
            .on("mouseover", function(d) {
                tooltip
                    .transition(200)
                    .style("display", "inline");
            })
            .on('mousemove', function(d) {
                var absoluteMousePos = d3.mouse(this);
                var absoluteMousePos = d3.mouse(that._svgContainer.node());
                var newX = (absoluteMousePos[0] + 20);
                var newY = (absoluteMousePos[1] - 20);
                tooltip
                    .text(d.props)
                    .attr('x', (newX) + "px")
                    .attr('y', (newY) + "px");

            })
            .on("mouseout", function(d) {
                tooltip
                    .transition(200)
                    .style("display", "none");
            });

        nodeEnter.append("circle")
            .attr("r", 1e-6)
            .style("fill", function(d) { return d._children ? "steelblue" : "#fff"; });

        nodeEnter.append("svg:a")
            .attr("target", "E2B")
            .attr("xlink:href", function(d) { return d.url; })
            .append("text")
            .attr("x", function(d) { return d.children || d._children ? -10 : 10; })
            .attr("dy", ".35em")
            .attr("text-anchor", function(d) { return d.children || d._children ? "end" : "start"; })
            .text(function(d) { return d.name; })
            .style("fill-opacity", 1e-6);

        // Transition nodes to their new position.
        var nodeUpdate = node.transition()
            .duration(this._cfg.duration)
            .attr("transform", function(d) { return "translate(" + d.y + "," + d.x + ")"; });

        nodeUpdate.select("circle")
            .attr("r", 4.5)
            .style("fill", function(d) { return d._children ? "steelblue" : "#fff"; });

        nodeUpdate.select("text")
            .style("fill-opacity", 1);

        // Transition exiting nodes to the parent's new position.
        var nodeExit = node.exit().transition()
            .duration(this._cfg.duration)
            .attr("transform", function(d) { return "translate(" + source.y + "," + source.x + ")"; })
            .remove();

        nodeExit.select("circle")
            .attr("r", 1e-6);

        nodeExit.select("text")
            .style("fill-opacity", 1e-6);

        // Update the links…
        var link = this._svgContainer.selectAll("path.link")
            .data(links, function(d) { return d.target.id; });

        // Enter any new links at the parent's previous position.
        var linkEnter = link.enter().insert("path", "g")
            .attr("class", "link")
            .attr("d", function(d) {
                var o = {x: source.x0, y: source.y0};
                return that._diagonal({source: o, target: o});
            })
            .attr("id", function(d) { return d.source.name + '-' + d.target.name; });

        var thing = this._svgContainer.selectAll("g.thing")
            .data(links, function(d) { return d.target.id; });

        // Enter any new linktexts at the parent's previous position.
        var thingEnter = thing.enter().append("g")
            .attr("class", "thing")

        thingEnter.append("text")
            .style("font-size", "20px")
            .append("textPath")
            .attr("xlink:href", function(d) { return '#' + d.source.name + '-' + d.target.name; })
            .style('text-anchor', "middle")
            .attr("startOffset", "50%")
            .text(function(d) { return d.target.transitiontext; })
            .on("mouseover", function(d) {
                tooltip
                    .transition(200)
                    .style("display", "inline");
            })
            .on('mousemove', function(d) {
                var absoluteMousePos = d3.mouse(this);
                var absoluteMousePos = d3.mouse(that._svgContainer.node());
                var newX = (absoluteMousePos[0] + 20);
                var newY = (absoluteMousePos[1] - 20);
                tooltip
                    .text(d.target.transitiontext)
                    .attr('x', (newX) + "px")
                    .attr('y', (newY) + "px");

            })
            .on("mouseout", function(d) {
                tooltip
                    .transition(200)
                    .style("display", "none");
            });

        thingEnter.append("use")
            .attr("xlink:href", function(d) { return '#' + d.source.name + '-' + d.target.name; })
            .style("stroke", "black")
            .style("fill", "none");

        var thingUpdate = thing.transition()
            .duration(0.2*this._cfg.duration);

        thingUpdate.select("text")
            .style("fill-opacity", 1);

        var thingExit = thing.exit().transition()
            .duration(0.2*this._cfg.duration)
            .remove();

        thingExit.select("text")
            .style("fill-opacity", 1e-6);

        // Transition links to their new position.
        link.transition()
            .duration(this._cfg.duration)
            .attr("d", that._diagonal);

        // Transition exiting nodes to the parent's new position.
        link.exit().transition()
            .duration(this._cfg.duration)
            .attr("d", function(d) {
                var o = {x: source.x, y: source.y};
                return that._diagonal({source: o, target: o});
            })
            .remove();

        // Stash the old positions for transition.
        nodes.forEach(function(d) {
            d.x0 = d.x;
            d.y0 = d.y;
        });

        // tooltip
        var tooltip = this._svg.selectAll(".tooltip").data([1]);

        // create tooltip
        tooltip
            .enter()
            .append('text')
            .attr('class', 'tooltip')
            .style('display', 'none')
            .style('fill', '#89a35c')
            .style('z-index', 1000000)
            .style('font-family', 'sans-serif')
            .style('font-size', '13px')
            .style('font-weight', 'bold');

        tooltip.exit().remove();

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

  methods : [ 'updateData', 'clear'],

  events: [ 'Selection' ]

} );