namespace( "rwt.client" );

rwt.client.CSSLoader = {

  load : function( params ) {
    if( params.files.length !== 1 ) {
      throw new Error( "CSSLoader does not support parallel file loading" );
    }
    rwt.remote.MessageProcessor.pauseExecution();
    this._loadFile( params.files[ 0 ] );
  },

  _loadFile : function( file ) {
    var cssElement = document.createElement( "link" );
    cssElement.rel = "stylesheet";
    cssElement.type = "text/css";
    cssElement.href = file;
    this._attachLoadedCallback( cssElement );
    document.getElementsByTagName( "head" )[ 0 ].appendChild( cssElement );
  },

  _attachLoadedCallback : function( cssElement ) {
    cssElement.onload = function() {
      rwt.remote.MessageProcessor.continueExecution();
      cssElement.onload = null;
    };
  }

};
