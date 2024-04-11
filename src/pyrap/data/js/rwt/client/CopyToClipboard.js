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

rwt.client.CopyToClipboard = function() {

    this.copy = function( text ) {
        console.log('got text: ', text);
        var el = document.createElement('textarea');
        el.value = text;
        el.setAttribute('readonly', '');
        el.style = {position: 'absolute', left: '-9999px'};
        document.body.appendChild(el);
        el.select();
        document.execCommand('copy');
        document.body.removeChild(el);
    };
};

rwt.client.CopyToClipboard.getInstance = function() {
  return rwt.runtime.Singletons.get( rwt.client.CopyToClipboard );
};
