pwt_ros3d = {};

pwt_ros3d.Simulation = function(parent, cssid, url, port, data) {
    this._urdfnodeDiv = this.createElement(parent);
    this._w = 800;
    this._h = 600;

    this._urdfnodeDiv.setAttribute('id', cssid ? cssid : 'urdf');
    this._rosliburl = url ? url : 'ws://prac.open-ease.org';
    this._roslibport = port ? port : '9090';
    this._urdfdata = data ? data : [];

    var that = this;
    parent.addListener( 'Resize', function() {
        that.setBounds( parent.getClientArea() );
    } );
    this.setBounds( parent.getClientArea() );
};

pwt_ros3d.Simulation.prototype = {

    createElement: function( parent ) {
        var clientarea = parent.getClientArea();
        var element = document.createElement( 'div' );
        element.style.position = 'absolute';
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        parent.append( element );
        return element;
    },

    setZIndex : function(index) {
        this._urdfnodeDiv.style.zIndex = index;
    },

    setBounds: function( args ) {
        this._urdfnodeDiv.style.left = args[0] + 'px';
        this._urdfnodeDiv.style.top = args[1] + 'px';
        this._urdfnodeDiv.style.width = args[2] + 'px';
        this._urdfnodeDiv.style.height = args[3] + 'px';
        if (typeof this._simulation_viewer != 'undefined') {
            this._simulation_viewer.resize(args[2], args[3]);
        }
     },

    destroy: function() {
        var element = this._urdfnodeDiv;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setWidth: function( width ) {
        this._w = width;
        this._urdfnodeDiv.style.width = width + 'px';
        if (typeof this._simulation_viewer != 'undefined') {
            this._simulation_viewer.style.width = width;
        }
    },

    setHeight: function( height ) {
        this._h = height;
        this._urdfnodeDiv.style.height = height + 'px';
        if (typeof this._simulation_viewer != 'undefined') {
            this._simulation_viewer.style.height = height;
        }
    },

    setUrl: function( url ) {
        this._rosliburl = url;
    },

    setPort: function ( port ) {
        this._roslibport = port;
    },

    setUrdfdata: function( data ) {
        this._urdfdata = data;
    },

    visualize: function() {

        console.log('Starting visualization on', this._rosliburl + ':' + this._roslibport, this._urdfdata);

        // remove all content from earlier simulations
        while (this._urdfnodeDiv.firstChild) {
            this._urdfnodeDiv.removeChild(this._urdfnodeDiv.firstChild);
        }

        // Connect to ROS.
        var ros = new ROSLIB.Ros({
          url : this._rosliburl + ':' + this._roslibport
        });

        // Create the main viewer.
        this._simulation_viewer = new ROS3D.Viewer({
          divID : this._urdfnodeDiv.attributes.id.value,
          width : this._w,
          height : this._h,
          antialias : true,
          cameraPose : {x : -3, y : 3, z : 3}//new THREE.Vector3(-3, 3, 3)//
        });

        // Add a grid.
        this._simulation_viewer.addObject(new ROS3D.Grid());

        // Setup a client to listen to TFs.
        var tfClient = new ROSLIB.TFClient({
          ros : ros,
          fixedFrame : 'map',
          angularThres : 0.01,
          transThres : 0.01,
          rate : 10.0
        });

        // Setup the marker client.
        var markerClient = new ROS3D.MarkerClient({
          ros : ros,
          tfClient : tfClient,
          topic : '/visualization_marker',
          path : 'http://svn.ai.uni-bremen.de/svn/sim_models/',
          rootObject : this._simulation_viewer.scene
        });

        // Setup the URDF client.
        var urdfClients = [];
        for (urdfData in this._urdfdata) {
            if('' == this._urdfdata[urdfData][1])
                urdfClients.push(new ROS3D.UrdfClient({
                                                      ros : ros,
                                                      tfClient : tfClient,
                                                      param : this._urdfdata[urdfData][0],
                                                      path : this._urdfdata[urdfData][2],
                                                      rootObject : this._simulation_viewer.scene,
                                                      loader : ROS3D.COLLADA_LOADER
                                                  }));
            else
                urdfClients.push(new ROS3D.UrdfClient({
                                                      ros : ros,
                                                      tfClient : tfClient,
                                                      param : this._urdfdata[urdfData][0],
                                                      tfPrefix : this._urdfdata[urdfData][1],
                                                      path : this._urdfdata[urdfData][2],
                                                      rootObject : this._simulation_viewer.scene,
                                                      loader : ROS3D.COLLADA_LOADER
                                                  }));
        }
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.ROS3D', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_ros3d.Simulation( parent, properties.cssid, properties.url, properties.port, properties.urdfdata);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'bounds', 'port', 'url', 'urdfdata', 'width', 'height'],

  methods : [ 'visualize' ],

  events: [ ]

} );