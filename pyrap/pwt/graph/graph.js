pwt_d3 = {};

pwt_d3.Graph = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3.select(this._parentDIV).append("div")
        .attr('class', 'graphtooltip')
        .style('z-index', 1000000);

    this.WAITMSEC = 200;
    this._linkdistance = 150;
    this._circleradius = 10;
    this._charge = -700;
    this._gravity = .1;
    this.force = d3.layout.force();
    this.nodes = this.force.nodes();
    this.links = this.force.links();
    this._markertypes = ["red", "green", "black", "blue"];

    this._svg = d3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.graph');
    this._defs = this._svgContainer.select('defs');

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

pwt_d3.Graph.prototype = {

    initialize: function() {

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'graph');
            this._svgContainer = this._svg.select('g.graph');
        }

        if (this._defs.empty()) {
            this._defs = this._svgContainer.append("defs");
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
        this._w = args[2];
        this._h = args[3];
        this.update();
    },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

    destroy: function() {
        var element = this._parentDIV;
        if ( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setWidth: function( width ) {
        this._parentDIV.style.width = width + "px";
        this._w = width;
        this.update();
    },

    /**
     * allows showing/hiding arrow heads and changing color
     * by appending respective css class
     * default: arrow heads shown, color #89a35c.
     */
    setArrow: function( arrow ) {
        this._markertypes.append(arrow);
        this.update();
    },

    setHeight: function( height ) {
        this._parentDIV.style.height = height + "px";
        this._h = height;
        this.update();
    },

    setCircleradius: function( radius ) {
        this._circleradius = radius;
        this.update();
    },


    setLinkdistance: function( distance ) {
        this._linkdistance = distance;
        this.update();
    },

    setCharge: function( charg ) {
        this._charge = charge;
        this.update();
    },


    setGravity: function( gravity ) {
        this._gravity = gravity;
        this.update();
    },

    updateData : function ( data ) {
        var toBeRemoved = data.remove;
        var toBeAdded = data.add;

        for (var remIdx = 0; remIdx < toBeRemoved.length; remIdx++) {
            this.removeLink(toBeRemoved[remIdx]);
        }

        for (var addIdx = 0; addIdx < toBeAdded.length; addIdx++) {
            this.addLink(toBeAdded[addIdx]);
        }
    },

    /**
     * replaces all nodes and links directly without fancy visualization
     */
    replaceData : function (data) {
        this.clear();
        for (var dataIndex = 0; dataIndex < data.length; dataIndex++) {
            if (this.findNodeIndex(data[dataIndex].source.name) === -1) {
                this.addNode(data[dataIndex].source.name, data[dataIndex].source.text, data[dataIndex].source.type, data[dataIndex].source.show);
            }
            if (this.findNodeIndex(data[dataIndex].target.name) === -1) {
                this.addNode(data[dataIndex].target.name, data[dataIndex].target.text, data[dataIndex].target.type, data[dataIndex].target.show);
            }
            this.links.push({"source": this.findNode(data[dataIndex].source),"target": this.findNode(data[dataIndex].target),"value": data[dataIndex].value, "arcStyle":data[dataIndex].arcStyle});
        }
        this.update();
    },

    /**
     * adds a node with the given id to the nodes list
     */
    addNode : function (id, text, type, show) {
        this.nodes.push({'id': id, 'text': text, 'type': type, 'show': show});
        this.update();
    },

    /**
     * removes a node with the given id
     */
    removeNode : function (id) {
        this.nodes.splice(this.findNodeIndex(id),1);
        this.update();
    },


    /**
     * adds a link if it does not exist yet, otherwise updates the edge label
     */
    addLink : function ( lnk ) {

        var src = this.findNode(lnk.source.name);
        var tgt = this.findNode(lnk.target.name);

        // if any of the link nodes does not exist, create it
        if (typeof src === 'undefined') {
            this.addNode(lnk.source.name, lnk.source.text, lnk.source.type, lnk.source.show);
            var src = this.findNode(lnk.source.name);
        }
        if (typeof tgt === 'undefined') {
            this.addNode(lnk.target.name, lnk.target.text, lnk.target.type, lnk.target.show);
            var tgt = this.findNode(lnk.target.name);
        }

        // check if there is already a link between src and tgt
        var index = this.findLinkIndex(src, tgt);
        if (index == -1) {
            // if not, create it
            this.links.push({"source": this.findNode(lnk.source.name),"target": this.findNode(lnk.target.name),"value": [lnk.value], "arcStyle": lnk.arcStyle, 'tttext': lnk.tttext ? lnk.tttext : ''});
        } else {
            // otherwise update link text
            this.links[index].value.push(lnk.value);
        }

        this.update();
    },

    /**
     * removes a link between two nodes or updates edge label
     */
    removeLink : function (lnk){
        var index = this.findLinkIndex(this.findNode(lnk.source.name), this.findNode(lnk.target.name));

        // if link actually exists
        if (index != -1) {
            // check if the value matches (multiple links between two nodes may exist)
            var valIndex = this.links[index].value.indexOf(lnk.value);
            if (valIndex != -1) {
                // remove the respective link value
                this.links[index].value.splice(valIndex, 1);
                if (this.links[index].value.length == 0) {
                    // delete the whole link if the value ends up empty, i.e.
                    // there are no link between the nodes anymore
                    this.links.splice(index, 1);
                }
            }
        }
        this.removeIfSingle(lnk.source.name);
        this.removeIfSingle(lnk.target.name);
        this.update();
    },

    /**
     * removes node if there are no links attached to it
     */
    removeIfSingle : function (id) {
        var isSingle = true;
        for (var j = 0; j < this.links.length; j++) {
            if (id == this.links[j].source.id || id == this.links[j].target.id) {
                isSingle = false;
            }
        }
        if (isSingle) {
            this.removeNode(id);
        }
    },

    /**
     * clear links list
     */
    removeAllLinks : function(){
        this.links.splice(0,this.links.length);
        this.update();
    },

    /**
     * clear nodes list
     */
    removeAllNodes : function(){
        this.nodes.splice(0,this.nodes.length);
        this.update();
    },

    /**
     * clear graph by emptying nodes and links lists
     */
    clear : function() {
        this.removeAllLinks();
        this.removeAllNodes();
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    retrievesvg : function ( args ) {
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, this._svg.node().outerHTML );
    },

    /**
     * returns the node with the given id
     */
    findNode : function(id) {
        for (var i in this.nodes) {
            if (this.nodes[i].id === id) return this.nodes[i];};
    },

    /**
     * returns the index of the link between source and target or -1 if there is no link
     */
    findNodeIndex : function(id) {
        for (var i = 0; i < this.nodes.length; i++) {
            if (this.nodes[i].id == id){
                return i;
            }
        }
        return -1;
    },

    /**
     * returns the index of the link between source and target or -1 if there is no link
     */
    findLinkIndex : function(source, target) {
        for (var i=0; i < this.links.length; i++) {
            if (this.links[i].source.id == source.id && this.links[i].target.id == target.id) {
                return i;
            }
        }
        return -1;
    },

    /**
     * redraws the graph with the updated nodes and links
     */
    update : function () {

        // no update before graph has been initialized
        if (!this._initialized) { return; }

        var that = this;

        this._markers = this._defs.selectAll("marker").data(this._markertypes);

        this._markers
              .enter()
              .append("marker")
              .attr("id", function(d) { return d; })
              .attr("viewBox", "0 -5 10 10")
              .attr("refX", 10)
              .attr("refY", -.8)
              .attr("markerWidth", 7.5)
              .attr("markerHeight", 7.5)
              .attr("orient", "auto")
              .append("path")
              .attr("d", "M0,-5L10,0L0,5 Z");

        this._markers.exit().remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LINKS                               ///
        ////////////////////////////////////////////////////////////////////////

        // select links
        var graphlinks = this._svgContainer.selectAll("path.graphlink").data(this.links, function(d) {return d.source.id + "-" + d.target.id;});

        // update links
        graphlinks
            .attr("id", function(d) { return d.source.id + "-" + d.target.id; })
            .attr("class", function(d) { return "graphlink " + d.arcStyle; })
            .attr("marker-end", function(d) {
                var split = d.arcStyle.split(' ');
                var as = split[split.length-1];
                return "url(#" + as + ")"; });

        // create links
        graphlinks
            .enter()
            .append("path")
            .attr("id", function(d) { return d.source.id + "-" + d.target.id; })
            .attr("class", function(d) { return "graphlink " + d.arcStyle; })
            .attr("marker-end", function(d) {
                var split = d.arcStyle.split(' ');
                var as = split[split.length-1];
                return "url(#" + as + ")"; })
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
                    .html(d.tttext)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                d3.select(this).style("cursor", "default");
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        // remove old links
        graphlinks.exit().remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE LINK LABELS                         ///
        ////////////////////////////////////////////////////////////////////////

        // select link labels
        var graphlinklabels = this._svgContainer.selectAll(".graphlinklabel").data(this.links, function(d) {return d.source.id + "-" + d.target.id;});

        // update link labels
        graphlinklabels
            .text(function(d){ return d.value.join(' / '); })
            .style("opacity", function(d) { return d.show ? 1 : 0; });

        // create link labels
        graphlinklabels
            .enter().append('text')
            .attr('class', 'graphlinklabel')
            .text(function(d){ return d.value.join(' / '); })
            .style("opacity", function(d) { return d.show ? 1 : 0; })
;

        // remove old link labels
        graphlinklabels.exit().remove();

        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE NODES                               ///
        ////////////////////////////////////////////////////////////////////////

        // select nodes
        var graphnodes = this._svgContainer.selectAll("g.graphnode").data(this.nodes, function(d) { return d.id; } );

        // create nodes group
        var graphnodesenter = graphnodes
                            .enter()
                            .append("g")
                            .attr("class", "graphnode")
                            .call(this.force.drag);

        // update nodes
        graphnodes.select('.graphcircle')
               .attr("dx", function (d) { return 0; }) // move inside rect
               .attr("dy", function (d) { return 0; }) // move inside rect
               .text(function (d) { return d.text; });

        // create nodes
        graphnodesenter.append("svg:circle")
            .attr('class', function(d) {
                return "graphcircle " + d.type;
            })
            .attr("r", function(d) {
                d.radius = 10;
                return d.radius;
            })
            .attr("id", function(d) { return d.id; } )
            .on("mouseover", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mousemove', function(d) {
                var newX = (d3.event.pageX + 20);
                var newY = (d3.event.pageY - 20);
                that._tooltip
                    .html(d.text)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });


        ////////////////////////////////////////////////////////////////////////
        ///                       UPDATE NODE LABELS                         ///
        ////////////////////////////////////////////////////////////////////////

        // update node labels
        graphnodes.select('.graphtext')
            .attr("dx", function (d) { return 5; }) // move inside rect
            .attr("dy", function (d) { return 15; }) // move inside rect
            .text( function(d) { return d.id; } )
            .style("opacity", function(d) { return d.show ? 1 : 0; });

        // create node labels
        graphnodesenter.append("svg:text")
            .attr("class","graphtext")
            .attr("dx", function (d) { return 5; }) // move inside rect
            .attr("dy", function (d) { return 15; }) // move inside rect
            .text( function(d) { return d.id; } )
            .style("opacity", function(d) { return d.show ? 1 : 0; });

        // remove old nodes
        graphnodes.exit().remove();

        var tick = function () {
            graphlinks.attr("d", linkArc);

            graphlinklabels
                .attr('d', linkArc)
                .attr('transform', rotatelabel)
                .attr('x', transformLabelX)
                .attr('y', transformLabelY);

            graphnodes.attr("transform", transform);
        };

        var rotatelabel = function (d) {
            var bbox = {};
            try {
                bbox = this.getBBox();
                // For Chrome
                if (!ie && !bbox.x && !bbox.y && !bbox.height && !bbox.width) {
                    bbox.x = this.attr('x');
                    bbox.y = this.attr('y');
                }
            } catch(e) {
            // Firefox 3.0.x plays badly here
            } finally {
                bbox = bbox || {};

            }

            var rx = bbox.x+bbox.width/2;
            var ry = bbox.y+bbox.height/2;
            var dX = d.target.x - d.source.x;
            var dY = d.target.y - d.source.y;
            var rad = Math.atan2(dX, dY);
            var deg = -90-rad * (180 / Math.PI);
            return 'rotate(' + deg +' '+rx+' '+ry+')';
        };

        var linkArc = function (d) {

            var dx = d.target.x - d.source.x,
                dy = d.target.y - d.source.y,
                dr = Math.sqrt(dx * dx + dy * dy);

                // offset to let arc start and end at the edge of the circle
                var offSetX = (dx * d.target.radius) / dr;
                var offSetY = (dy * d.target.radius) / dr;
            return "M" +
                (d.source.x + offSetX) + "," +
                (d.source.y + offSetY) + "A" +
                dr + "," + dr + " 0 0,0 " +
                (d.target.x - offSetX) + "," +
                (d.target.y - offSetY);
        };

        // move arc label to arc
        var calcLabelPos = function (d, bbox) {
            var scale = 0.4; // distance from arc
            var origPos = { x: (d.source.x + d.target.x ) /2 - bbox.width/2, y: (d.source.y + d.target.y) /2 }; // exact middle between source and target
            var dir = { x: d.target.x - d.source.x, y: d.target.y - d.source.y }; // direction source -> target
            var rot = { x: dir.y, y: -dir.x }; // rotate direction -90 degrees
            var ltemp = Math.sqrt(rot.x * rot.x + rot.y * rot.y) / 100; // normalize length
            var length = ltemp !== 0 ? ltemp : 0.1; // if length is 0, set to small value to prevent NaN
            var rotNorm = { x: rot.x / length, y: rot.y / length }; // normalize rotation direction
            return { x: origPos.x - scale * rotNorm.x, y: origPos.y - scale * rotNorm.y};// return moved position
        };

        var transform = function (d) {
            return "translate(" + d.x + "," + d.y + ")";
        };

        var transformLabel = function (d) {
            return "translate(" + d.source.x + "," + d.source.y + ")";
        };

        var transformLabelX = function (d) {
            var bbox = {};
            try {
                bbox = this.getBBox();
                // For Chrome
                if (!ie && !bbox.x && !bbox.y && !bbox.height && !bbox.width) {
                    bbox.x = this.attr('x');
                    bbox.y = this.attr('y');
                }
            } catch(e) {
            // Firefox 3.0.x plays badly here
            } finally {
                bbox = bbox || {};

            }
            return calcLabelPos(d, bbox).x;
        };

        var transformLabelY = function (d) {
            var bbox = {};
            try {
                bbox = this.getBBox();
                // For Chrome
                if (!ie && !bbox.x && !bbox.y && !bbox.height && !bbox.width) {
                    bbox.x = this.attr('x');
                    bbox.y = this.attr('y');
                }
            } catch(e) {
            // Firefox 3.0.x plays badly here
            } finally {
                bbox = bbox || {};

            }
            return calcLabelPos(d, bbox).y;
        };

        this.force
            .size([this._w, this._h])
            .linkDistance( this._linkdistance )
            .charge( this._charge )
            .on("tick", tick)
            .gravity( this._gravity )
            .start();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Graph', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_d3.Graph( parent, properties);
    },

    destructor: 'destroy',

    properties: [ 'remove', 'width', 'height', 'linkdistance', 'circleradius', 'charge', 'gravity', 'bounds', 'arrow'],

    methods : [ 'updateData', 'clear', 'retrievesvg'],

    events: [ 'Selection' ]

} );