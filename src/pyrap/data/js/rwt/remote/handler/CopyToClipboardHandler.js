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

rwt.remote.HandlerRegistry.add( "rwt.client.CopyToClipboard", {

  factory : function() {
    return rwt.client.CopyToClipboard.getInstance();
  },

  service : true,

  destructor : rwt.util.Functions.returnTrue,

  methods : [
    "copy"
  ],

  methodHandler : {
    "copy" : function( object, args ) {
      object.copy( args.text );
    }
  }

} );
