namespace( "rwt.client" );

rwt.client.CSSLoader = {

  linkCss : function( params ) {
    if( params.files.length !== 1 ) {
      throw new Error( "CSSLoader does not support parallel file loading" );
    }
    rwt.remote.MessageProcessor.pauseExecution();
    this._linkCss( params.files[ 0 ] );
  },

  _linkCss : function( file ) {
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
  },
  
  loadCss : function( params ) {
    rwt.remote.MessageProcessor.pauseExecution();
    this._loadCss( params.content );
  },

  _loadCss : function( content ) {
    var cssElement = document.createElement( "style" );
    cssElement.type = "text/css";
    cssElement.innerHTML = content;
    this._attachLoadedCallback( cssElement );
    document.getElementsByTagName( "head" )[ 0 ].appendChild( cssElement );
  },

};
