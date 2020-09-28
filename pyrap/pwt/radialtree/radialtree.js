// adapted from https://bl.ocks.org/wmleler/a734fb2bb3319a2cb386
pwt_radialtree = {};

pwt_radialtree.RadialTree = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._tooltip = d3v3.select(this._parentDIV).append("div")
        .attr('class', 'radialtreetooltip')
        .style('z-index', 1000000);

    this._svg = d3v3.select(this._parentDIV).append("svg");
    this._svgContainer = this._svg.select('g.radialtree');
    this._defs = this._svgContainer.select('defs');

    this._cfg = {
        padding: 100,
        duration: 700,
        ndelay: 4,
        ddelay: 200,
        nradius: 3,
        minzoom: 0.5,
        maxzoom: 10,
        defcolor: 'steelblue',
        selcolor: 'green',
        zoomfactor: 0.04,
        pan: 3,
        rot: 1.5,
        w: 800,
        h: 800,
        glow: false,
        fontcolor: null
	};

    this._keycodes = {
        KEY_PLUS: 187,     // + (zoom in)
        KEY_MINUS: 189,    // - (zoom out)
        KEY_SLASH: 191,    // / (slash)
        KEY_PAGEUP: 33,    // (rotate CCW)
        KEY_PAGEDOWN: 34,  // (rotate CW)
        KEY_LEFT: 37,      // left arrow
        KEY_UP: 38,        // up arrow
        KEY_RIGHT: 39,     // right arrow
        KEY_DOWN: 40,      // down arrow
        KEY_SPACE: 32,     // (expand node)
        KEY_RETURN: 13,    // (expand tree)
        KEY_HOME: 36,      // (center root)
        KEY_END: 35        // (center selection)
    };

    this._counter = 0;  // node ids
    this._curNode = null;  // currently selected node
    this._curPath = [];  // array of nodes in the path to the currently selected node

    // current pan, zoom, and rotation
    this._curX = this._cfg.w / 2;
    this._curY = this._cfg.h / 2;
    this._curZ = 1.0; // current zoom
    this._curR = 270; // current rotation

    this._startposX = null;
    this._startposY = null; // initial position on mouse button down for pan

    this._keysdown = [];  // which keys are currently down
    this._moveX = 0;
    this._moveY = 0;
    this._moveZ = 0;
    this._moveR = 0; // animations
    this._aniRequest = null;
    this._aniTime = null;

    this._transition = null;
    this._timestamp = null;

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

pwt_radialtree.RadialTree.prototype = {

    initialize: function() {

        var that = this;

        if (this._svgContainer.empty()) {
            this._svg
                .attr('width', "100%")
                .attr('height', "100%")
                .append( "svg:g" )
                .attr('class', 'radialtree')
                .attr('transform', 'translate(' + this._curX + ',' + this._curY + ')');
            this._svgContainer = this._svg.select('g.radialtree');
        }

        // d3v3 tree layout
        this._tree = d3v3.layout.tree()
            .size([360, Math.min(this._cfg.w, this._cfg.h) / 2 - this._cfg.padding])
            .separation(function(a, b) {
                return a.depth === 0 ? 1 : (a.parent === b.parent ? 1 : 2) / a.depth;
            });

        d3v3.select(document) // set up document events
            .on('wheel', function() {
                that.wheel(that); })  // zoom, rotate
            .on('keydown', function(e) {
                that.keydown(that, e); })
            .on('keyup', function(e) {
                that.keyup(e, that); });

        this._svg // set up document events
            .on('mousedown', function(e) {
                that.mousedown(that); });

        d3v3.select('#selection')
            .on('mousedown', function(e) {
                that.switchroot(that); });

        d3v3.select('#contextmenu')
            .on('mouseup', function(e) {
                that.menuSelection(that); });

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

        if (typeof args[2] != 'undefined' && typeof args[3] != 'undefined' ) {
            var oldwidth = this._cfg.w;
            var oldheight = this._cfg.h;
            this._cfg.w = Math.min(args[2],args[3]);
            this._cfg.h = this._cfg.w;
            this._curX += (this._cfg.w - oldwidth) / 2;
            this._curY += (this._cfg.h - oldheight) / 2;

            if (typeof this._tree != 'undefined'){
                this._tree.size([360, Math.min(this._cfg.w, this._cfg.h) / 2 - this._cfg.padding]);
            }

            this._svgContainer
                .attr('transform', 'rotate(' + this._curR + ' ' + this._curX + ' ' + this._curY + ')translate(' + this._curX + ' ' + this._curY + ')scale(' + this._curZ + ')');
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
        rwt.remote.Connection.getInstance().getRemoteObject( this ).set( args.type, [this._svg.node().outerHTML, args.fname] );
    },

    setGlow: function ( glow ) {
        this._cfg.glow = glow;
        this.update();
    },

    setFontcolor: function ( fc ) {
        this._cfg.fontcolor = fc;
        this.update();
    },

    /**
     * retrieves the svg as text to save it to a file
     */
    diagonal : function(x) {
        return d3v3.svg.diagonal.radial()
            .projection(function(d) {
                return [d.y, d.x / 180 * Math.PI];
            })(x);
    },

    /**
     * Toggle expand / collapse
     */
    toggle : function(d) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else if (d._children) {
            d.children = d._children;
            d._children = null;
        }
    },

    toggleTree : function(d, that) {
        if (d.children) {
            that.collapseTree(d);
        } else {
            that.expandTree(d, that);
        }
    },

    expand : function(d) {
        if (d._children) {
            d.children = d._children;
            d._children = null;
        }
    },

    /**
     * expand all children, whether expanded or collapsed
     */
    expandTree : function(d, that) {
        if (d._children) {
            d.children = d._children;
            d._children = null;
        }
        if (d.children) {
            d.children.forEach(function(el) {
                that.expandTree(el, that);
            });
        }
    },

    /**
     * collapse children of selected Node
     */
    collapse : function( d ) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        }
    },

    /**
     * collapse all children
     */
    collapseTree : function( d, that ) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        }
        if (d._children) {
            d._children.forEach(that.collapseTree);
        }
    },

    /**
     * expand one tree level
     */
    expand1Level : function(d) {
        var q = [d]; // non-recursive
        var cn;
        var done = null;
        while (q.length > 0) {
            cn = q.shift();
            if (done !== null && done < cn.depth) { return; }
            if (cn._children) {
                done = cn.depth;
                cn.children = cn._children;
                cn._children = null;
                cn.children.forEach(collapse);
            }
            if (cn.children) { q = q.concat(cn.children); }
        }
        // no nodes to open
    },

    /**
     * highlight selected node
     */
    selectNode : function(node, that) {
        if (that._curNode) {
            delete that._curNode.selected;
        }
        that._curNode = node;
        that._curNode.selected = true;
        that._curPath = []; // filled in by fullpath
        d3v3.select('#selection').html(that.fullpath(node, that));
    },

    /**
     * for displaying full path of node in tree
     */
    fullpath : function(d, that, idx) {
        idx = idx || 0;
        that._curPath.push(d);
        return (d.parent ? that.fullpath(d.parent, that, that._curPath.length) : '') +
            '/<span class="nodepath'+(d.name === that._root.name ? ' highlight' : '')+
            '" data-sel="'+ idx +'" title="Set Root to '+ d.name +'">' +
        d.name + '</span>';
    },

    switchroot : function(that) {
        d3v3.event.preventDefault();
        var pathelms = document.querySelectorAll('#selection .nodepath');
        for (var i = 0; i < pathelms.length; i++) {
            pathelms[i].classList.remove('highlight');
        }
        var target = d3v3.event.target;
        var node = that._curPath[+target.dataset.sel];
        if (d3v3.event.shiftKey) {
            if (that._curNode !== node) {
                that.selectNode(node, that);
            }
        } else {
            that._data = node;
            target.classList.add('highlight');
        }
        this._transition = true;
        that.update();
    },

    click : function(d, that) { // select node
        if (d3v3.event.defaultPrevented || d === that._curNode) { return; } // suppressed
        d3v3.event.preventDefault();
        that.selectNode(d, that);
        that.update(d);
    },

    dblclick : function(d, that) {  // Toggle children of node
        if (d3v3.event.defaultPrevented) { return; } // click suppressed
        d3v3.event.preventDefault();
        if (d3v3.event.shiftKey) {
            that.expand1Level(d); // expand node by one level
        } else {
            that.toggle(d);
        }
        that._root = d;
        that._transition = true;
        that.update();
    },

    tooldown : function(d, that) {  // tool button pressed
        d3v3.event.preventDefault();
        d3v3.select(d3v3.event.target)
            .on('mouseout', that.toolup);
        var key = +d3v3.event.target.dataset.key;
        that.keydown(that, Math.abs(key), key < 0 || d3v3.event.shiftKey);
    },

    toolup : function(that) {  // tool button released
        d3v3.event.preventDefault();
        d3v3.select(d3v3.event.target)
            .on('mouseout', null);
        that.keyup(Math.abs(+d3v3.event.target.dataset.key), that);
    },

    // right click, show context menu and select this node
    showContextMenu : function(d, that) {
        rwt.remote.Connection.getInstance().getRemoteObject( that ).notify( "Selection", { args: { func: 'context'},
                                                                                           item: { name: d.name, id: d.id },
                                                                                           x: d3v3.event.pageX,
                                                                                           y: d3v3.event.pageY } );
    },

    hideContextMenu : function() {
        d3v3.select('#contextmenu').style('display', 'none');
        d3v3.select(document).on('mouseup', null);
    },

    menuSelection : function(that) {
        d3v3.event.preventDefault();
        var key = +d3v3.event.target.dataset.key;
        that.keydown(that, Math.abs(key), key < 0 || d3v3.event.shiftKey);
    },

    mousedown : function(that) {  // pan
        d3v3.event.preventDefault();

        cancelAnimationFrame(that._aniRequest);
        that._aniRequest = that._aniTime = null;

        if (d3v3.event.which !== 1 || d3v3.event.ctrlKey) { return; } // ingore other mouse buttons
        that._startposX = that._curX - d3v3.event.clientX;
        that._startposY = that._curY - d3v3.event.clientY;
        d3v3.select(document)
            .on('mousemove', function() {that.mousemove(that)}, true);
        d3v3.select(document)
            .on('mouseup', function() {that.mouseup(that)}, true);
    },

    mousemove : function(that) {
        d3v3.event.preventDefault();
        that._curX = that._startposX + d3v3.event.clientX;
        that._curY = that._startposY + d3v3.event.clientY;
        that.setview(that);
    },

    mouseup : function() {
        d3v3.select(document)
            .on('mousemove', null);
        d3v3.select(document)
            .on('mouseup', null);
    },

    wheel : function(that) {  // mousewheel
        that._timestamp = Date.now();

        if (d3v3.event.deltaY > 0) {  // down
            that._moveR = -that._cfg.rot; // rotate counterclockwise
        }
        if (d3v3.event.deltaY < 0) {  // up
            that._moveR = that._cfg.rot; // rotate clockwise
        }

        if (that._aniRequest === null) {
            that._aniRequest = requestAnimationFrame(that.frame(that));
        }

        setTimeout(function(){
            if (Date.now() - that._timestamp > 200) {
                    cancelAnimationFrame(that._aniRequest);
                    that._aniRequest = that._aniTime = null;
                    that._moveR = 0;
            }
        }, 250);


        that._zoomdir = d3v3.event.deltaY;
    },

    // keyboard shortcuts
    keydown : function(that, key, shift) {
        cancelAnimationFrame(that._aniRequest);
        that._aniRequest = that._aniTime = null;

        if (!key) {
            key = d3v3.event.which;  // fake key
            shift = d3v3.event.shiftKey;
        }
        var parch; // parent's children
        var slow = d3v3.event.altKey ? 0.25 : 1;
        if (that._keysdown.indexOf(key) >= 0) { return; } // defeat auto repeat
        switch (key) {
            case that._keycodes.KEY_PLUS: // zoom in
                that._moveZ = that._cfg.zoomfactor * slow;
                break;
            case that._keycodes.KEY_MINUS: // zoom out
                that._moveZ = -that._cfg.zoomfactor * slow;
                break;
            case that._keycodes.KEY_SLASH: // toggle root to selection
                that._data = that._data === that._curNode ? that._data : that._curNode;
                that.update();
                that._curPath = []; // filled in by fullpath
                d3v3.select('#selection').html(fullpath(that._curNode, that));
                return;
            case that._keycodes.KEY_PAGEUP: // rotate counterclockwise
                that._moveR = -that._cfg.rot * slow;
                break;
            case that._keycodes.KEY_PAGEDOWN: // zoom out
                that._moveR = that._cfg.rot * slow; // rotate clockwise
                break;
            case that._keycodes.KEY_LEFT: // left arrow
                if (shift) { // move selection to parent
                    if (!that._curNode) {
                        that.selectNode(that._data, that);
                    } else if (that._curNode.parent) {
                        that.selectNode(that._curNode.parent, that);
                    }
                    that.update(that._curNode);
                    return;
                    }
                that._moveX = -that._cfg.pan * slow;
                break;
            case that._keycodes.KEY_UP: // up arrow
                if (shift) { // move selection to previous child
                    if (!that._curNode) {
                        that.selectNode(that._data, that);
                    } else if (that._curNode.parent) {
                        parch = that._curNode.parent.children;
                        that.selectNode(parch[(parch.indexOf(that._curNode) +
                        parch.length - 1) % parch.length], that);
                    }
                    that.update(that._curNode);
                    return;
                }
                that._moveY = -that._cfg.pan * slow;
                break;
            case that._keycodes.KEY_RIGHT: // right arrow
                if (shift) { // move selection to first/last child
                    if (!that._curNode) {
                        that.selectNode(that._data, that);
                    } else {
                        if (that._curNode.children) {
                            that.selectNode(that._curNode.children[d3v3.event.altKey ?
                            that._curNode.children.length - 1 : 0], that);
                        }
                    }
                    that.update(that._curNode);
                    return;
                }
                that._moveX = that._cfg.pan * slow;
                break;
            case that._keycodes.KEY_DOWN: // down arrow
                if (shift) { // move selection to next child
                    if (!that._curNode) {
                        that.selectNode(that._data, that);
                    } else if (that._curNode.parent) {
                        parch = that._curNode.parent.children;
                        that.selectNode(parch[(parch.indexOf(that._curNode) + 1) % parch.length], that);
                    }
                    that.update(that._curNode);
                    return;
                }
                that._moveY = that._cfg.pan * slow;
                break;
            case that._keycodes.KEY_SPACE: // expand/collapse node
                if (!that._curNode) {
                    that.selectNode(that._data, that);
                }
                toggle(that._curNode);
                that.update(that._curNode, true);
                return;
            case that._keycodes.KEY_RETURN: // expand/collapse tree
                if (!that._curNode) {
                    that.selectNode(that._data, that);
                }
                if (shift) {
                    that.expandTree(that._curNode);
                } else {
                    that.expand1Level(that._curNode);
                }
                that.update(that._curNode, true);
                return;
            case that._keycodes.KEY_HOME: // reset transform
                if (shift) {
                    that._data = that._data;
                }
                that._curX = that._cfg.w / 2;
                that._curY = that._cfg.h / 2;
                that._curR = that.limitR(90 - that._root.x);
                that._curZ = 1;
                that.update(root, true);
                return;
            case that._keycodes.KEY_END: // zoom to selection
                if (!that._curNode) { return; }
                that._curX = that._cfg.w / 2 - that._curNode.y * that._curZ;
                that._curY = that._cfg.h / 2;
                that._curR = that.limitR(90 - that._curNode.x);
                that.update(that._curNode, true);
                return;
            default: return;  // ignore other keys
        } // break jumps to here
        that._keysdown.push(key);
        // start animation if anything happening
        if (that._keysdown.length > 0 && that._aniRequest === null) {
            that._aniRequest = requestAnimationFrame(that.frame(that));
        }
    },

    keyup : function(key, that) {
        key = key || d3v3.event.which;
        var pos = that._keysdown.indexOf(key);
        if (pos < 0) { return; }

        switch (key) {
            case that._keycodes.KEY_PLUS: // zoom out
            case that._keycodes.KEY_MINUS: // zoom in
                that._moveZ = 0;
                break;
            case that._keycodes.KEY_PAGEUP: // rotate CCW
            case that._keycodes.KEY_PAGEDOWN: // rotate CW
                that._moveR = 0;
                break;
            case that._keycodes.KEY_LEFT: // left arrow
            case that._keycodes.KEY_RIGHT: // right arrow
                that._moveX = 0;
                break;
            case that._keycodes.KEY_UP: // up arrow
            case that._keycodes.KEY_DOWN: // down arrow
                that._moveY = 0;
                break;
        }
        that._keysdown.splice(pos, 1);  // remove key
        if (that._keysdown.length > 0 || that._aniRequest === null) { return; }
        cancelAnimationFrame(that._aniRequest);
        that._aniRequest = that._aniTime = null;
    },

    frame : function(that) {
        return function(frametime) {
            var diff = that._aniTime ? (frametime - that._aniTime) / 16 : 0;
            that._aniTime = frametime;

            var dz = Math.pow(1.2, diff * that._moveZ);
            var newZ = that.limitZ(that._curZ * dz, that);
            dz = newZ / that._curZ;
            that._curZ = newZ;
            that._curX += diff * that._moveX - (that._cfg.w / 2- that._curX) * (dz - 1);
            that._curY += diff * that._moveY - (that._cfg.h / 2 - that._curY) * (dz - 1);
            that._curR = that.limitR(that._curR + diff * that._moveR);
            that.setview(that);
            that._aniRequest = requestAnimationFrame(that.frame(that));
        };
    },

    // enforce zoom extent
    limitZ : function(z, that) {
        return Math.max(Math.min(z, that._cfg.maxzoom), that._cfg.minzoom);
    },

    // keep rotation between 0 and 360
    limitR : function(r) {
        return (r + 360) % 360;
    },

    // limit size of text and nodes as scale increases
    reduceZ : function(that) {
        return Math.pow(1.1, -that._curZ);
    },

    // set view with no animation
    setview : function(that) {
        that._svgContainer
            .attr('transform', 'rotate(' + that._curR + ' ' + that._curX + ' ' + that._curY + ')translate(' + that._curX + ' ' + that._curY + ')scale(' + that._curZ + ')');

        that._svgContainer.selectAll('.rtnode text')
            .attr('text-anchor', function(d) {
                return (d.x + that._curR) % 360 <= 180 ? 'start' : 'end';
            })
            .attr('transform', function(d) {
                return ((d.x + that._curR) % 360 <= 180 ? 'translate(8)scale(' : 'rotate(180)translate(-8)scale(' ) + that.reduceZ(that) +')';
            });

        that._svgContainer.selectAll('circle')
            .attr('r', 2*that._cfg.nradius * that.reduceZ(that));
    },

    /**
     * that.updates data options
     */
    setData : function ( data ) {

        // treeData
        this._data = data;

        this._root = data;
        this._transition = true;

        this._root.x0 = this._curY;
        this._root.y0 = 0;
        this.selectNode(this._root, this); // current selected node
        this.expandTree(this._root, this);

        this._dataloaded = true;

        this.update();
        rap._.notify('render');
    },


    /**
     * redraws the radar chart with the that.updated datapoints and polygons
     */
    update : function () {

        // no that.update before graph has been initialized
        if (!this._initialized) { return; }
        if (!this._dataloaded) { return; }

        var that = this;

        // add glow filters
        this._filters = this._defs.selectAll('filter').data(['circle', 'path']);

        this._filters
            .enter()
            .append("filter")
            .attr("id", function(d) { return "glow-" + d; })
            .append("feGaussianBlur")
            .attr("class", "glow")
            .attr("stdDeviation", function(d) { return d === 'path' ? 0.5 : 0.6; })
            .attr("result","coloredBlur");

        this._filters
            .exit()
            .remove();

        // TODO: get these values somewhere
        var source = this._data;
        var transition = this._transition;

        var duration = transition ? (d3v3.event && d3v3.event.altKey ? this._cfg.duration * 4 : this._cfg.duration) : 0;

        // Compute the new tree layout.
        var nodes = this._tree.nodes(this._data);
        var links = this._tree.links(nodes);

        // Update the view
        this._svgContainer
            .transition()
            .duration(this._cfg.duration)
            .attr('transform', 
                'rotate(' + this._curR + ' ' + this._curX + ' ' + this._curY + 
                ')translate(' + this._curX + ' ' + this._curY + 
                ')scale(' + this._curZ + ')');
    
        // NODES
        var node = this._svgContainer.selectAll('g.rtnode').data(nodes, function(d) { return d.id || (d.id = ++that._counter); });
    
        // create nodes
        var nodeEnter = node
            .enter()
            .insert('g', ':first-child')
            .attr('class', 'rtnode')
            .attr('transform', 'rotate(' + (source.x0 - 90) + ')translate(' + source.y0 + ')')
            .on('click', function(d) { that.click(d, that); })
            .on('dblclick', function(d) { that.dblclick(d, that); })
            .on('contextmenu', function(d) { that.showContextMenu(d, that); })
            .on("mouseover", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "block");
            })
            .on('mousemove', function(d) {
                var newX = (d3v3.event.pageX + 20);
                var newY = (d3v3.event.pageY - 20);
                that._tooltip
                    .html(d.tooltip)
                    .style("left", (newX) + "px")
                    .style("top", (newY) + "px");
            })
            .on("mouseout", function(d) {
                that._tooltip
                    .transition(200)
                    .style("display", "none");
            });

        nodeEnter
            .append('circle')
            .attr('r', 1e-6)
            .style("fill", function(d) {
                return d.type ? d.type : 'steelblue';
            })
            .style("stroke", function(d) {
                return d.type ? d.type : 'steelblue';
            })
            .on('dblclick', function(d) { that.dblclick(d, that); })
            .style('fill-opacity', function(d) {
                return d._children ? 1 : 0.1;
            });

        nodeEnter
            .append('text')
            .text(function(d) {
                return ((typeof d.showname === 'undefined' || d.showname) && d.name) ? d.name : '';
            })
            .style('opacity', 0.9)
            .style('fill-opacity', 0)
            .attr('transform', function() {
                return ((source.x0 + that._curR) % 360 <= 180 ? 'translate(8)scale(' : 'rotate(180)translate(-8)scale(') + that.reduceZ(that) + ')';
            });
    
        // update nodes: change circle fill depending on whether it has children and is collapsed
        var nodeUpdate = node
            .transition()
            .duration(duration)
            .delay( transition ? function(d, i) {
                return i * that._cfg.ndelay + Math.abs(d.depth - that._curNode.depth) * that._cfg.ddelay; }  : 0)
            .attr('transform', function(d) {
                return 'rotate(' + (d.x - 90) + ')translate(' + d.y + ')';
            });
    
        nodeUpdate.select('circle')
            .attr('r', function(d) {
                return (d.selected ? 5 : 2) * that._cfg.nradius * that.reduceZ(that);
            })
            .style("filter", this._cfg.glow ? "url(#glow-circle)" : "none")
            .style('fill-opacity', function(d) {
                return d._children ? 1 : null;
            })
            .style('stroke-width', function(d) {
                return d.selected ? 5 : null;
            });

        nodeUpdate.select('text')
            .attr('text-anchor', function(d) {
                return (d.x + that._curR) % 360 <= 180 ? 'start' : 'end';
            })
            .attr('transform', function(d) {
                return ((d.x + that._curR) % 360 <= 180 ? 'translate(8)scale(' : 'rotate(180)translate(-8)scale(' ) + that.reduceZ(that) +')';
            })
            .style('fill', this._cfg.fontcolor)
            .attr('dy', '.35em')
            .style('fill-opacity', 1);
    
        // remove nodes: exiting nodes to the parent's new position and remove
        var nodeExit = node
            .exit()
            .transition()
            .duration(duration)
            .delay( transition ? function(d, i) {
                return i * that._cfg.ndelay; } : 0)
            .attr('transform', function() {
                return 'rotate(' + (source.x - 90) +')translate(' + source.y + ')';
            })
            .remove();
    
        nodeExit.select('circle')
            .attr('r', 0);

        nodeExit.select('text')
            .style('fill-opacity', 0);
    
        // EDGES
        var link = this._svgContainer.selectAll('g.rtedge').data(links, function(d) { return d.target.id; });

        var linkenter = link
            .enter()
            .append('g')
            .attr('class', 'rtedge');

        // create links
        linkenter
            .insert('path', 'g')
            .style("stroke", function(d) {
                return d.target.type ? d.target.type : '#ccc';
            })
            .attr("id", function(d) {
                var str = d.source.name + '-' + d.target.name;
                return str.replace(" ", "_"); })
            .attr('d', function() {

            var o = {
                x: source.x0,
                y: source.y0
            };
            return that.diagonal({
                source: o,
                target: o
            });
        });

        linkenter
            .append("text")
            .style("font-size", "15px")
            .append("textPath")
            .attr("href", function(d) {
                var str = d.source.name + '-' + d.target.name;
                return '#' + str.replace(" ", "_"); })
            .style('text-anchor', "middle")
            .attr("startOffset", "50%")
            .text(function(d) { return ((typeof d.target.showedge === 'undefined' || d.target.showedge) && d.target.edgetext) ? d.target.edgetext : ''; })
            .on("mouseover", function() {
                that._tooltip
                    .transition(200)
                    .style('display', 'block');
            })
            .on('mousemove', function(d) {
                var newX = (d3v3.event.pageX + 20);
                var newY = (d3v3.event.pageY - 20);
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

        linkenter
            .append("use")
            .attr("href", function(d) { return '#' + d.source.name + '-' + d.target.name; })
            .style("stroke", "none")
            .style("fill", "none");

        // update links: transition links to their new position
        var linkupdate = link
            .transition()
            .duration(duration);

        linkupdate
            .select('path')
            .delay( transition ? function(d, i) {
                return i * that._cfg.ndelay + Math.abs(d.source.depth - that._curNode.depth) * that._cfg.ddelay;
            } : 0)
            .attr('d', function(d) {
                return that.diagonal(d);})
            .attr('class', 'rtlink');

        linkupdate
            .select("text")
            .style("fill-opacity", 1);

        linkupdate
            .select("text textPath")
            .attr("href", function(d) {
                var str = d.source.name + '-' + d.target.name;
                return '#' + str.replace(" ", "_"); })
            .style('text-anchor', "middle")
            .attr("startOffset", "50%")
            .text(function(d) { return ((typeof d.target.showedge === 'undefined' || d.target.showedge) && d.target.edgetext) ? d.target.edgetext : ''; });

        linkupdate
            .select('use')
            .attr("href", function(d) { return '#' + d.source.name + '-' + d.target.name; })
            .style("stroke", "none")
            .style("fill", "none");

        // remove links
        var linkexit = link
            .exit()
            .transition()
            .duration(duration);

        linkexit
            .select("text")
            .style("fill-opacity", 1e-6);

        linkexit
            .select("use")
            .remove();

        linkexit
            .select('path')
            .attr('d', function() {
                var o = {
                    x: source.x0,
                    y: source.y0
                };
                return that.diagonal({
                    source: o,
                    target: o
                });
            })
            .remove();

        linkexit
            .remove();
    
        // Stash the old positions for transition
        nodes.forEach(function(d) {
          d.x0 = d.x;
          d.y0 = d.y;
        });

    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.RadialTree', {

    factory: function( properties ) {
        var parent = rap.getObject( properties.parent );
        return new pwt_radialtree.RadialTree( parent, properties.options);
    },

    destructor: 'destroy',
    properties: [ 'remove', 'width', 'height', 'data', 'bounds', 'glow', 'fontcolor'],
    methods : [ 'clear', 'retrievesvg'],
    events: [ 'Selection' ]

} );