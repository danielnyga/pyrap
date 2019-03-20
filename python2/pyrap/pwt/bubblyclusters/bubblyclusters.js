// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_bubblyclusters = {};

pwt_bubblyclusters.BubblyClusters = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._p = parent;
    this._data = [];

    this._padding = 1.5; // separation between same-color nodes
    this._clusterPadding = 6; // separation between different-color nodes
    this._maxRadius = 12;

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.bubblyclusters');

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

pwt_bubblyclusters.BubblyClusters.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'bubblyclusters')
                .attr("transform", "translate(" + (this._wwidth/2) + "," + (this._wheight/2) + ")");
            this._svgContainer = this._svg.select('g.bubblyclusters');
        }
        this.update();
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
        if (this._svgContainer.node() !== null ) {
            var bbox = this._svgContainer.node().getBBox();
            this._svgContainer
                .attr("transform", "translate(" + (bbox.width/2) + "," + (bbox.height/2) + ")");
        }
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
        this.this._parentDIV.style.height = height + "px";
        this._h = height;
        this.update();
    },


    /**
     * removes all axes from the radar chart
     */
    clear : function ( ) {
        this.setData( {} );
    },


    /**
     * updates data options
     */
    setData : function ( data ) {
        this._data = data;
        this._distinctclusters = this.distinct(this._data);
        this._clusters = new Array(this._distinctclusters.length);
        this.update();
    },

    /**
     *
     * @param cls
     * @returns {*}
     */
    distinct : function(cls) {

        var contains = function(olist, el){
            for(var i=0; i<olist.length; i++){
                if (olist[i].cluster === el.cluster) {
                    return [true, i];
                }
            }
            return [false, -1];
        };

        var clusters = [];
        for(var i=0; i<cls.length; i++){
            var cnt = contains(clusters, cls[i]);
            if (!cnt[0]) {
                clusters.push(cls[i]);
            }
            else if (cls[i].radius > clusters[cnt[1]].radius) {
                clusters[cnt[1]] = cls[i];
            }
        }
        clusters.sort((a,b) => a.cluster > b.cluster ? 1 : b.cluster > a.cluster ? -1 : 0);
        return clusters;
    },


    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        // cleanup/(re-)initialize data
        this._nodes = [];
        this._clusters = this.distinct(this._data);
        this._color = d3.scale.category10().domain(d3.range(this._clusters.length));
        this._cwidth = this._w > 0 ? this._w : 960;
        this._cheight = this._h > 0 ? this._h : 600;

        this._nodes = d3.range(this._data.length).map(function(i) {
            var y = Math.floor(Math.random() * that._distinctclusters.length);
            var d = {
                cluster: that._data[i].cluster,
                radius: that._data[i].radius,
                x: Math.cos(y / that._distinctclusters.length * 2 * Math.PI) * 200 + that._cwidth / 2 + Math.random(),
                y: Math.sin(y / that._distinctclusters.length * 2 * Math.PI) * 200 + that._cheight / 2 + Math.random()
            };
            return d;
        });

        this._force = d3.layout.force()
            .nodes(this._nodes)
            .size([this._cwidth, this._cheight])
            .gravity(.02)
            .charge(0)
            .on("tick", tick)
            .start();

        // select nodes
        var node = this._svgContainer.selectAll("circle").data(this._nodes);

        // create nodes
        node
            .enter()
            .append("circle")
            .style("fill", function(d) { return that._color(d.cluster); })
            .on('mouseover', function(d, i) {})
            .call(this._force.drag);

        // update nodes
        node
            .transition()
            .duration(750)
            .delay(function(d, i) { return i * 5; })
            .attrTween("r", function(d) {
                var i = d3.interpolate(0, d.radius);
                return function(t) {
                    return d.radius = i(t);
                };
            });

        function tick(e) {
            node
                .each(cluster(10 * e.alpha * e.alpha))
                .each(collide(.5))
                .attr("cx", function(d) { return d.x; })
                .attr("cy", function(d) { return d.y; });
        }

        // Move d to be adjacent to the cluster node.
        function cluster(alpha) {
            console.log('cluster alpha', alpha);
            return function(d) {
                var cluster = that._clusters[d.cluster];
                if (cluster === d) return;
                var x = d.x - cluster.x,
                y = d.y - cluster.y,
                l = Math.sqrt(x * x + y * y),
                r = d.radius + cluster.radius;
                if (l !== r) {
                    l = (l - r) / l * alpha;
                    d.x -= x *= l;
                    d.y -= y *= l;
                    cluster.x += x;
                    cluster.y += y;
                }
            };
        }

        // Resolves collisions between d and all other circles.
        function collide(alpha) {
            var quadtree = d3.geom.quadtree(that._nodes);
            return function(d) {
                var r = d.radius + that._maxRadius + Math.max(that._padding, that._clusterPadding),
                nx1 = d.x - r,
                nx2 = d.x + r,
                ny1 = d.y - r,
                ny2 = d.y + r;
                quadtree.visit(function(quad, x1, y1, x2, y2) {
                    if (quad.point && (quad.point !== d)) {
                        var x = d.x - quad.point.x,
                        y = d.y - quad.point.y,
                        l = Math.sqrt(x * x + y * y),
                        r = d.radius + quad.point.radius + (d.cluster === quad.point.cluster ? that._padding : that._clusterPadding);
                        if (l < r) {
                            l = (l - r) / l * alpha;
                            d.x -= x *= l;
                            d.y -= y *= l;
                            quad.point.x += x;
                            quad.point.y += y;
                        }
                    }
                    return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1;
                });
            };
        }

        // remove old nodes
        node.exit().remove();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.BubblyClusters', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_bubblyclusters.BubblyClusters( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds'],
    methods : [ 'updateData', 'clear', 'highlight'],
    events: [ 'Selection' ]

} );