/*******************************************************************************
 * Copyright (c) 2010, 2015 EclipseSource and others.
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Eclipse Public License v1.0
 * which accompanies this distribution, and is available at
 * http://www.eclipse.org/legal/epl-v10.html
 *
 * Contributors:
 *    EclipseSource - initial API and implementation
 ******************************************************************************/

rwt.qx.Class.define( "rwt.widgets.GC", {

  extend : rwt.qx.Object,

  construct : function( control ) {
    this.base( arguments );
    this._control = control;
    this._control.addEventListener( "create", this._onControlCreate, this );
    this._canvas = null;
    this._context = null;
    this._createCanvas();
    this._canvas.rwtObject = this; // like "rwtWidget" in Widget.js, useful for custom JS components
    if( this._control.isCreated() ) {
      this._addCanvasToDOM();
    }
    this._linearGradient = null;
  },

  destruct : function() {
    this._control.removeEventListener( "create", this._onControlCreate, this );
    if( this._control.isCreated() && !this._control.isDisposed() ) {
      this._removeCanvasFromDOM();
    }
    this._control = null;
    this._canvas.rwtObject = null;
    this._canvas = null;
    if( this._context.dispose ) {
      this._context.dispose();
    }
    this._context = null;
  },

  members : {

    init : function( width, height, font, background, foreground  ) {
      this._canvas.width = width;
      this._canvas.style.width = width + "px";
      this._canvas.height = height;
      this._canvas.style.height = height + "px";
      this._context.clearRect( 0, 0, width, height );
      this._initFields( font, background, foreground );
      this._control.dispatchSimpleEvent( "paint" ); // client-side painting on server-side redraw
    },

    /**
     * Executes drawing operations using the HTML5-Canvas 2D-Context syntax.
     * Only a subset is supported on all browser, especially IE is limited.
     * Each operation is an array starting with the name of the function to call, followed
     * by its parameters. Properties are treated the same way, i.e. [ "propertyName", "value" ].
     * Other differences from official HTML5-Canvas API:
     *  - Colors are to be given as array ( [ red, green blue ] )
     *  - "addColorStop" will automatically applied to the last created gradient.
     *  - To assign the last created linear gradient as a style, use "linearGradient" as the value.
     *  - strokeText behaves like fillText and fillText draws a rectangular background
     *  - ellipse is not a W3C standard, only WHATWG, but we need it for SWT arc to work.
     */
    draw : function( operations ) {
      for( var i = 0; i < operations.length; i++ ) {
        try {
          var op = operations[ i ][ 0 ];
          switch( op ) {
            case "fillStyle":
            case "strokeStyle":
            case "globalAlpha":
            case "lineWidth":
            case "lineCap":
            case "lineJoin":
            case "font":
              this._setProperty( operations[ i ] );
            break;
            case "createLinearGradient":
            case "addColorStop":
            case "fillText":
            case "strokeText":
            case "ellipse":
            case "drawImage":
            case "drawGrid":
              this[ "_" + op ]( operations[ i ] );
            break;
            default:
              this._context[ op ].apply( this._context, operations[ i ].slice( 1 ) );
            break;
          }
        } catch( ex ) {
          var opArrStr = "[ " + operations[ i ].join( ", " ) + " ]";
          throw new Error( "Drawing operation failed: " + opArrStr + " :" + ex.message );
        }
      }
    },

    getNativeContext : function() {
      return this._context;
    },

    ////////////
    // Internals

    _createCanvas : function() {
      this._canvas = document.createElement( "canvas" );
      this._context = this._canvas.getContext( "2d" );
    },

    _onControlCreate : function() {
      this._addCanvasToDOM();
    },

    _addCanvasToDOM  : function() {
      var controlElement = this._control._getTargetNode();
      var firstChild = controlElement.firstChild;
      if( firstChild ) {
        controlElement.insertBefore( this._canvas, firstChild );
      } else {
        controlElement.appendChild( this._canvas );
      }
    },

    _removeCanvasFromDOM : function() {
      this._canvas.parentNode.removeChild( this._canvas );
    },

    _initFields : function( font, background, foreground ) {
      this._context.strokeStyle = rwt.util.Colors.rgbaToRgbaString( foreground );
      this._context.fillStyle = rwt.util.Colors.rgbaToRgbaString( background );
      this._context.globalAlpha = 1.0;
      this._context.lineWidth = 1;
      this._context.lineCap = "butt";
      this._context.lineJoin = "miter";
      this._context.font = this._toCssFont( font );
      this._context.textBaseline = "top";
      this._context.textAlign = "left";
    },

    // See http://www.whatwg.org/specs/web-apps/current-work/multipage/the-canvas-element.html#building-paths
    _ellipse : function( operation ) {
      var cx = operation[ 1 ];
      var cy = operation[ 2 ];
      var rx = operation[ 3 ];
      var ry = operation[ 4 ];
      //var rotation = operation[ 5 ]; // not supported
      var startAngle = operation[ 6 ];
      var endAngle = operation[ 7 ];
      var dir = operation[ 8 ];
      if( rx > 0 && ry > 0 ) {
        this._context.save();
        this._context.translate( cx, cy );
        // TODO [tb] : using scale here changes the stroke-width also, looks wrong
        this._context.scale( 1, ry / rx );
        this._context.arc( 0, 0, rx, startAngle, endAngle, dir );
        this._context.restore();
      }
    },

    _setProperty : function( operation ) {
      var property = operation[ 0 ];
      var value = operation[ 1 ];
      if( value === "linearGradient" ) {
        value = this._linearGradient;
      } else if( property === "fillStyle" || property === "strokeStyle" ) {
        value = rwt.util.Colors.rgbaToRgbaString( value );
      } else if( property === "font" ) {
        value = this._toCssFont( value );
      }
      this._context[ property ] = value;
    },

    _strokeText : function( operation ) {
      var text = this._prepareText.apply( this, operation.slice( 1, 5 ) );
      var lines = text.split( "\n" );
      var textBounds = this._getTextBounds.apply( this, operation.slice( 1, 7 ) );
      this._drawText( lines, textBounds, false, operation.slice( 7, 9 ));
    },

    _fillText : function( operation ) {
      var text = this._prepareText.apply( this, operation.slice( 1, 5 ) );
      var lines = text.split( "\n" );
      var textBounds = this._getTextBounds.apply( this, operation.slice( 1, 7 ) );
      this._drawText( lines, textBounds, true, operation.slice( 7, 9 ));
    },

    _drawText : function( textLines, bounds, fill, align ) {
      this._context.save();
      var lineHeight = bounds[ 3 ] / textLines.length;
      var maxlength = bounds[2];
      for( var i = 0; i < textLines.length; i++ ) {
          var fontProps = {};
          rwt.html.Font.fromString( this._context.font ).renderStyle( fontProps );
          var x = align[0] ? bounds[ 0 ] - rwt.widgets.util.FontSizeCalculation.computeTextDimensions( textLines[ i ], fontProps )[0]/2 : bounds[ 0 ];
          var y = align[1] ? bounds[ 1 ] - bounds[ 3 ] / 2 + i * lineHeight  : i * lineHeight + bounds[ 1 ];
          if( fill ) {
                this._context.fillText( textLines[ i ], x, y );
          } else {
                this._context.strokeText( textLines[ i ], x, y );
          }
      }
      this._context.restore();
    },

    _drawGrid : function( operation ) {
        this._context.save();
        var stepwidthX = operation[1];
        var stepwidthY = operation[2];
        var bw = this._canvas.width;
        var bh = this._canvas.height;

        for (var x = 0; x <= bw; x += stepwidthX) {
                this._context.moveTo(x, 0);
                this._context.lineTo(x, bh);
            }

        for (var y = 0; y <= bh; y += stepwidthY) {
            this._context.moveTo(0, y);
            this._context.lineTo(bw, y);
        }

        this._context.strokeStyle = operation[3];
        this._context.lineWidth = 1;
        this._context.stroke();
        this._context.restore();
    },

    _drawImage : function( operation ) {
      var args = operation.slice( 1 );
      var image = new Image();
      image.src = args[ 0 ];
      args[ 0 ] = image;
      // On (native) canvas, only loaded images can be drawn:
      if( image.complete ) {
        this._context.drawImage.apply( this._context, args );
      } else {
        var alpha = this._context.globalAlpha;
        var context = this._context;
        image.onload = function() {
          // TODO [tb] : The z-order will be wrong in this case.
          context.save();
          context.globalAlpha = alpha;
          context.drawImage.apply( context, args );
          context.restore();
        };
      }
    },

    _createLinearGradient : function( operation ) {
      var func = this._context.createLinearGradient;
      this._linearGradient = func.apply( this._context, operation.slice( 1 ) );
    },

    _addColorStop : function( operation ) {
      this._linearGradient.addColorStop(
        operation[ 1 ],
        rwt.util.Colors.rgbToRgbString( operation[ 2 ] )
      );
    },

    _prepareText : function( value, drawMnemonic, drawDelemiter, drawTab ) {
      var EncodingUtil = rwt.util.Encoding;
      var text = drawMnemonic ? EncodingUtil.removeAmpersandControlCharacters( value ) : value;
      var replacement = drawDelemiter ? "\n" : "";
      text = EncodingUtil.replaceNewLines( text, replacement );
      replacement = drawTab ? "    " : "";
      text = text.replace( /\t/g, replacement );
      return text;
    },

    _getTextBounds : function( text, drawMnemonic, drawDelemiter, drawTab, x, y ) {
      var escapedText = this._escapeText( text, drawMnemonic, drawDelemiter, drawTab );
      var fontProps = {};
      rwt.html.Font.fromString( this._context.font ).renderStyle( fontProps );
      var calc = rwt.widgets.util.FontSizeCalculation;
      var dimension = calc.computeTextDimensions( escapedText, fontProps );
      return [ x, y, dimension[ 0 ], dimension[ 1 ] ];
    },

    _escapeText : function( value, drawMnemonic, drawDelemiter, drawTab ) {
      var EncodingUtil = rwt.util.Encoding;
      var text = EncodingUtil.escapeText( value, drawMnemonic );
      var replacement = drawDelemiter ? "<br/>" : "";
      text = EncodingUtil.replaceNewLines( text, replacement );
      replacement = drawTab ? "&nbsp;&nbsp;&nbsp;&nbsp;" : "";
      text = text.replace( /\t/g, replacement );
      return text;
    },

    _toCssFont : function( fontArray ) {
      var result = "";
      if( fontArray[ 3 ] ) {
        result += "italic ";
      }
      if( fontArray[ 2 ] ) {
        result += "bold ";
      }
      result += fontArray[ 1 ] + "px ";
      result += fontArray[ 0 ].join( "," );
      return result;
    }

  }
} );
