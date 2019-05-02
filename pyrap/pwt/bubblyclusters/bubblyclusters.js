// based on code from https://github.com/alangrafu/radar-chart-d3
// check http://nbremer.blogspot.nl/2013/09/making-d3-radar-chart-look-bit-better.html
// for extra information
pwt_bubblyclusters = {};

pwt_bubblyclusters.BubblyClusters = function( parent, audio ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'bubblytooltip')
        .style('z-index', 1000000);

    this._padding = 1.5; // separation between same-color nodes
    this._clusterPadding = 6; // separation between different-color nodes
    this._maxRadius = 12;
    this._force = d3.layout.force();
    this._color = d3.scale.ordinal()
        .range(['#e41a1c','#0a4db8','#4daf4a','#984ea3','#ff7f00','#ffff33','#a65628','#f781bf','#999999',
                '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a', '#d62728', '#ff9896', '#9467bd',
                '#c5b0d5', '#8c564b', '#c49c94', '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
                '#17becf', '#9edae5']);

    this._audio = false;
    if (audio) {
        this._sound = new Audio(audio);
        this._audio = true;
    }

    this._w = 800;
    this._h = 600;

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
                .attr('class', 'bubblyclusters');
            this._svgContainer = this._svg.select('g.bubblyclusters');
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
     * Load audio file
     */
    setAudio : function( audiofile ) {
        this._sound = new Audio(audiofile);
        this._audio = true;
    },

    /**
     * Play sound
     */
    play: function() {
        if (this._audio) {
            var audioClone = this._sound.cloneNode();
            audioClone.play();
        }
    },

    /**
     * Pause sound
     */
    pause: function() {
        if (this._audio) {
            this._sound.pause();
        }
    }
    ,
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
        this._nodes = data;
        this._clusters = new Array(this.distinct(this._nodes));
        this._color.domain(Object.keys(this._clusters));

        var that = this;

        this._nodes.forEach(function(n) {
            n.x = Math.cos(n.cluster / that._clusters.length * 2 * Math.PI) * that._w / 2 + Math.random();
            n.y = Math.sin(n.cluster / that._clusters.length * 2 * Math.PI) * that._h / 2 + Math.random();
            if (!that._clusters[n.cluster] || (n.radius > that._clusters[n.cluster].radius)) that._clusters[n.cluster] = n;
        });

        this._dataloaded = true;
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
        return clusters.length;
    },

    /**
     * redraws the radar chart with the updated datapoints and polygons
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }
        if (!this._dataloaded) { return; }

        var that = this;

        var node = this._svgContainer.selectAll('g.bubblynode').data(this._nodes);

        // circle groups creation
        var nodeenter = node
            .enter()
            .append('g')
            .attr("class", "bubblynode");

        // circle creation
        nodeenter
            .append("circle")
            .attr("class", "bubbly")
            .style("fill", function(d) { return that._color(d.cluster); })
            .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.tooltip ? d.tooltip : '')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .on("click", function(d) {
                rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'button': 'left', args:{} } );
            })
            .on("contextmenu", function (d) {
                rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { 'button': 'right', args:{} } );
            })
            .transition()
            .duration(1000)
            .delay(function(d, i) { that.play(); return i * 5; })
            .attrTween("r", function(d) {
                var i = d3.interpolate(0, d.radius);
                return function(t) {
                    return i(t);
                };
            });

        node.select('.bubbly')
            .call(this._force.drag);

        // node and node text update
        function tick(e) {
            node.select('.bubbly')
                .each(cluster(20 * e.alpha * e.alpha))
                .each(collide(.5))
                .attr("cx", function(d) { return d.x; })
                .attr("cy", function(d) { return d.y; });

            node.select('.bubblytext')
                .each(cluster(20 * e.alpha * e.alpha))
                .each(collide(.5))
                .attr("dx", function(d) { return d.x - 4; })
                .attr("dy", function(d) { return d.y + 5; });
        }

        // text creation
        nodeenter
            .append("text")
            .attr("class", "bubblytext")
                        .on("mouseover", function(d) {
                d3.select(this).style("cursor", "pointer");
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.tooltip ? d.tooltip : '')
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            })
            .text(function(d){return that._clusters[d.cluster] === d ? d.cluster : ''});

        node.select('.bubblytext')
            .call(this._force.drag);

        // Move d to be adjacent to the cluster node.
        function cluster(alpha) {
            return function(d) {
                var cluster = that._clusters[d.cluster];
                if (cluster === d) return;
                var x = d.x - cluster.x,
                    y = d.y - cluster.y,
                    l = Math.sqrt(x * x + y * y),
                    r = d.radius + cluster.radius;
                if (l !== r) {
                    l = (l - r) / l * alpha / Math.min(10, (d.clustersize ? d.clustersize : 10));
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

        this._force
            .nodes(this._nodes)
            .size([this._w, this._h])
            .gravity(.02)
            .charge(0)
            .on("tick", tick)
            .start();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.BubblyClusters', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_bubblyclusters.BubblyClusters( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds', 'audio'],
    methods : [ 'clear', 'retrievesvg', 'play'],
    events: [ 'Selection' ]

} );