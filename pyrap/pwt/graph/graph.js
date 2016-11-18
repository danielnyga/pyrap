pwt_d3 = {};

pwt_d3.Graph = function( parent, cssid ) {

    this.WAITMSEC = 100;
    this.width = window.innerWidth;
    this.height = window.innerHeight;
    this.force = d3.layout.force();
    this.nodes = this.force.nodes();
    this.links = this.force.links();

    this._parentDIV = this.createElement(parent);

    if (cssid) {
        this._parentDIV.setAttribute('id', cssid);
    }

    this._svg = d3.select(this._parentDIV)
        .append("svg");

    this._needsLayout = true;
    this._needsRender = true;
    var that = this;
    rap.on( "render", function() {
        if( that._needsRender ) {
            if( that._needsLayout ) {
                that.initialize( that );
                that._needsLayout = false;
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

        this._svgContainer = this._svg.select('g');
        if (this._svgContainer.empty()) {
            this._svg
            .attr('width', this.width)
            .attr('height', this.height)
            .append( "svg:g" );
            this._svgContainer = this._svg.select('g');
        }

        if (this._svgContainer.select('defs').empty()) {
            this._svgContainer.append("defs").selectAll("marker")
                  .data(["dashedred", "strokegreen", "dashed", "strokeblue", "arrowhead", "default"])
                  .enter().append("marker")
                  .attr("id", function(d) { return d; })
                  .attr("viewBox", "0 -5 10 10")
                  .attr("refX", 10)
                  .attr("refY", -.8)
                  .attr("markerWidth", 7.5)
                  .attr("markerHeight", 7.5)
                  .attr("orient", "auto")
                  .append("path")
                  .attr("d", "M0,-5L10,0L0,5 Z");
        }
        this.update();
    },

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        parent.append( element );
        return element;
    },

     setBounds: function( args ) {
        this._parentDIV.style.left = args[0] + "px";
        this._parentDIV.style.top = args[1] + "px";
        this._parentDIV.style.width = args[2] + "px";
        this._parentDIV.style.height = args[3] + "px";
     },

    setZIndex : function(index) {
        this._parentDIV.style.zIndex = index;
    },

     _scheduleUpdate: function( needsLayout ) {
        if( needsLayout ) {
            this._needsLayout = true;
        }
        this._needsRender = true;
    },

    destroy: function() {
        var element = this._parentDIV;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    _resize: function( clientArea ) {
        this.width = clientArea[ 2 ];
        this.height = clientArea[ 3 ];
        this.update();
    },

    setwidth: function( width ) {
        this.width = width;
        this.update();
    },


    setheight: function( height ) {
        this.height = height;
        this.update();
    },


    /**
     * updates nodes and links with timeout to have a bouncy visualization
     */
    updateData : function ( data ) {
      var toBeRemoved = data.remove;
      var toBeAdded = data.add;

      var nodesCopy = this.nodes.slice();

      var removeLinks = function(dIndex, that) {
        var rInterval = setTimeout( function() {
          if (dIndex < toBeRemoved.length) {
            that.removeLink(toBeRemoved[dIndex]);
            that.removeIfSingle(toBeRemoved[dIndex].source.name);
            that.removeIfSingle(toBeRemoved[dIndex].target.name);
            dIndex++;
          }
          if (dIndex < toBeRemoved.length) {
            removeLinks(dIndex, that);
          } else {
            addNodesAndLinks(0, that);
          }
        }, that.WAITMSEC);
      };

      var addNodesAndLinks = function(dataIndex, that) {
        var aInterval = setTimeout( function() {
          if (dataIndex < toBeAdded.length) {
            if (that.findNodeIndex(toBeAdded[dataIndex].source.name) === -1) {
              that.addNode(toBeAdded[dataIndex].source.name, toBeAdded[dataIndex].source.text);
            }
            if (that.findNodeIndex(toBeAdded[dataIndex].target.name) === -1) {
              that.addNode(toBeAdded[dataIndex].target.name, toBeAdded[dataIndex].target.text);
            }
            that.addLink(toBeAdded[dataIndex]);
            dataIndex++;
          }
          if (dataIndex < toBeAdded.length) {
            addNodesAndLinks(dataIndex, that);
          } else {
            console.log('Finished updating graph');
          }
        }, that.WAITMSEC);
      };

      removeLinks(0, this);
    },

    /**
     * replaces all nodes and links directly without fancy visualization
     */
    replaceData : function (data) {
      this.clear();
      for (var dataIndex = 0; dataIndex < data.length; dataIndex++) {
        if (this.findNodeIndex(data[dataIndex].source.name) === -1) {
              this.addNode(data[dataIndex].source.name, data[dataIndex].source.text);
            }
            if (this.findNodeIndex(data[dataIndex].target.name) === -1) {
              this.addNode(data[dataIndex].target.name, data[dataIndex].target.text);
            }
        this.links.push({"source": this.findNode(data[dataIndex].source),"target": this.findNode(data[dataIndex].target),"value": data[dataIndex].value, "arcStyle":data[dataIndex].arcStyle});
      }
      this.update();
    },

    /**
     * adds a node with the given id to the nodes list
     */
    addNode : function (id, tttext) {
      this.nodes.push({"id":id, 'text': tttext});
    //      this.playSound();
      this.update();
    },

    /**
     * removes a node with the given id
     */
    removeNode : function (id) {
      this.nodes.splice(this.findNodeIndex(id),1);
    //      this.playSound();
      this.update();
    },

    /**
     * adds a link if it does not exist yet, otherwise updates the edge label
     */
    addLink : function (lnk){
      var index = this.findLinkIndex(this.findNode(lnk.source.name), this.findNode(lnk.target.name));
      if (index == -1) {
        this.links.push({"source": this.findNode(lnk.source.name),"target": this.findNode(lnk.target.name),"value": [lnk.value], "arcStyle": lnk.arcStyle});
      } else {
        var valIndex = this.links[index].value.indexOf(lnk.value);
        if (valIndex == -1) {
          // whole link has to be removed and re-added, used for redrawing
          var tempLink = this.links[index];
          this.links.splice(index, 1);
          this.update();
          tempLink.value.push(lnk.value);
          this.links.push(tempLink);
        }
      }
      this.update();
    },

    /**
     * removes a link between two nodes or updates edge label
     */
    removeLink : function (lnk){
      var index = this.findLinkIndex(this.findNode(lnk.source.name), this.findNode(lnk.target.name));
      if (index != -1) {
        var valIndex = this.links[index].value.indexOf(lnk.value);
        if (valIndex != -1) {
          var tempLink = this.links[index];
          this.links.splice(index, 1);
          this.update();
          tempLink.value.splice(valIndex, 1);
          if (!tempLink.value.length == 0) {
            this.update();
            this.links.push(tempLink);
          }
        }
      }
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
     * clone audio object to play sound synchronously
     */
    playSound : function() {
      var audioClone = this.audio.cloneNode();
      audioClone.play();
    },


    /**
     * redraws the graph with the updated nodes and links
     */
    update : function () {

      var path = this._svgContainer.selectAll("path.link")
        .data(this.links, function(d) {
                return d.source.id + "-" + d.target.id;
                });

      var pathEnter = path.enter().append("path")
        .attr("id", function(d) { return d.source.id + "-" + d.target.id; })
        .attr("class", function(d) { return "link " + d.arcStyle; })
        .attr("marker-end", function(d) { return "url(#" + d.arcStyle + ")"; });

      path.exit().remove();

      var edgelabels = this._svgContainer.selectAll(".label")
            .data(this.links, function(d) {
                return d.source.id + "-" + d.target.id;
                });

      var edgelabelsEnter = edgelabels.enter().append('text')
          .style("pointer-events", "none")
          .attr('class', 'label')
          .text(function(d){ return d.value.join(' / '); });

      edgelabels.exit().remove();

      var circle = this._svgContainer.selectAll("g.node")
        .data(this.nodes, function(d) { return d.id; } );

      var circleEnter = circle.enter().append("g")
        .attr("class", "node")
        .call(this.force.drag);

      circleEnter.append("svg:circle")
        .on("mouseover", function(d) {
            //Get this bar's x/y values, then augment for the tooltip
           circleEnter.append("text")
          .attr("id", "tooltip")
          .attr("dx", function (d) { return 0; }) // move inside rect
          .attr("dy", function (d) { return 0; }) // move inside rect
          .attr("text-anchor", "middle")
          .attr("font-family", "sans-serif")
          .attr("font-size", "11px")
          .attr("font-weight", "bold")
          .attr("fill", "black")
          .text(d.text);
        })
        .on("mouseout", function() {
            //Remove the tooltip
            d3.select("#tooltip").remove();
        })
        .attr("r", function(d) {
          d.radius = 10;
          return d.radius; } )
        .attr("id", function(d) { return d.id; } );

      circleEnter.append("svg:text")
        .attr("class","textClass")
        .attr("dx", function (d) { return 5; }) // move inside rect
        .attr("dy", function (d) { return 15; }) // move inside rect
        .text( function(d) { return d.id; } );

      circle.exit().remove();


      var tick = function () {
        path.attr("d", linkArc);
        edgelabels.attr('d', linkArc);
        edgelabels.attr('transform', rotateLabel);
        edgelabels.attr('x', transformLabelX);
        edgelabels.attr('y', transformLabelY);
        circle.attr("transform", transform);
      };

      var rotateLabel = function (d) {
        var bbox = this.getBBox();
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
        var bbox = this.getBBox();
        return calcLabelPos(d, bbox).x;
      };

      var transformLabelY = function (d) {
        var bbox = this.getBBox();
        return calcLabelPos(d, bbox).y;
      };

      this.force
        .size([this.width, this.height])
        .linkDistance( this.height/2 )
        .charge(-700)
        .on("tick", tick)
        .gravity( .1 )
        .distance( 200 )
        .start();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Graph', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_d3.Graph( parent, properties.cssid);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height' ],

  methods : [ 'updateData' ],

  events: [ ]

} );