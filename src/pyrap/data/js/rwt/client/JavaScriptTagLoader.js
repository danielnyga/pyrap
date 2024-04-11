/*******************************************************************************
 * Copyright (c) 2012, 2014 EclipseSource and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *    EclipseSource - initial API and implementation
 ******************************************************************************/

namespace( "rwt.client" );

rwt.client.JavaScriptTagLoader = {

  load : function( params ) {
    if( params.code.length == 0 ) {
      throw new Error( "JavaScriptTagLoader will not create empty tag" );
    }
    rwt.remote.MessageProcessor.pauseExecution();
    this._loadFile( params.code );
  },

  _loadFile : function( code ) {
    var scriptElement = document.createElement( "script" );
    scriptElement.type = "text/javascript";
    scriptElement.innerHTML = code;
    this._attachLoadedCallback( scriptElement );

    var head = document.getElementsByTagName( "head" )[ 0 ];
    head.appendChild( scriptElement );

  },

  _attachLoadedCallback : function( scriptElement ) {
    scriptElement.onload = function() {
      rwt.remote.MessageProcessor.continueExecution();
      scriptElement.onload = null;
    };
  }

};
