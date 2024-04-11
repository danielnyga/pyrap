rwt.remote.HandlerRegistry.add( "rwt.client.CSSLoader", {

  factory : function() {
    return rwt.client.CSSLoader;
  },

  service : true,

  methods : [
    "linkCss", 
    "loadCss"
  ]

} );