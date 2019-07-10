pwt_audio = {};

pwt_audio.Audio = function( parent ) {

    this._parentDIV = this.createElement(parent);
    this._audio = this._parentDIV.getElementsByTagName('audio')[0];
    this._sources = [];

    var that = this;
    parent.addListener( "Resize", function() {
        that.setBounds( parent.getClientArea() );
    } );
};

pwt_audio.Audio.prototype = {

    createElement: function( parent ) {
        // create surrounding div
        var clientarea = parent.getClientArea();
        var element = document.createElement( "div" );
        element.style.position = "absolute";
        element.style.left = clientarea[0];
        element.style.top = clientarea[1];
        element.style.width = clientarea[2];
        element.style.height = clientarea[3];

        // create audio element
        var vid = document.createElement( "audio" );
        vid.style.width = "100%";
        vid.style.height = "100%";

        // append audio to surrounding div
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
     * adds a source to the audio
     * (e.g. src = {source: http://path/to/audio.{mp4,ogg}, type: audio/{mp4,ogg}}
     */
    addSrc : function ( src ) {
        var srcElement = document.createElement('source');
        srcElement.src = src.source;
        srcElement.type = src.type;
        this._sources.push(srcElement);
        this._audio.append(srcElement);
    },

    /**
     * updates data options
     */
    remSrc : function ( src ) {
        // TODO
    },


    /**
     * Play audio
     */
    play: function() {
        this._audio.play();
    },

    /**
     * Pause audio
     */
    pause: function() {
        this._audio.pause();
    }
};

// Type handler
rap.registerTypeHandler( 'pwt.customs.Audio', {

  factory: function( properties ) {
    var parent = rap.getObject( properties.parent );
    return new pwt_audio.Audio( parent, properties);
  },

  destructor: 'destroy',

  properties: [ 'remove', 'width', 'height', 'bounds'],

  methods : [ 'play', 'pause', 'clear', 'addSrc'],

  events: [ 'Selection' ]

} );