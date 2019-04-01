pwt_video = {};

pwt_video.Video = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._video = this._parentDIV.getElementsByTagName('video')[0];
    this._sources = [];

    var that = this;
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
};

pwt_video.Video.prototype = {

    createElement: function( parent ) {
        // create surrounding div
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = clientarea[2];
        element.style.height = clientarea[3];

        // create video element
        var vid = document.createElement( "video" );
        vid.style.width = "100%";
        vid.style.height = "100%";

        // append video to surrounding div
        element.append( vid );

        // append surrounding div to parent element
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

    destroy: function() {
        var element = this._parentDIV;
        if( element.parentNode ) {
            element.parentNode.removeChild( element );
        }
    },

    setWidth: function( width ) {
        this._parentDIV.style.width = width + "px";
    },

    setHeight: function( height ) {
        this._parentDIV.style.height = height + "px";
    },

    /**
     * adds a source to the video
     * (e.g. src = {source: http://path/to/video.{mp4,ogg}, type: video/{mp4,ogg}}
     */
    addSrc : function ( src ) {
        var srcElement = document.createElement('source');
        srcElement.src = src.source;
        srcElement.type = src.type;
        this._sources.push(srcElement);
        this._video.append(srcElement);
    },

    /**
     * updates data options
     */
    remSrc : function ( src ) {
        // TODO
    },


    /**
     * Play video
     */
    play: function() {
        this._video.play();
    },

    /**
     * Pause video
     */
    pause: function() {
        this._video.pause();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Video', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_video.Video( parent, properties);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height', 'bounds'],

  methods : [ 'play', 'pause', 'clear', 'addSrc'],

  events: [ 'Selection' ]

} );