//---allow for dynamic loading
Ext.Loader.setConfig({
    enabled: true
});
//---Remove trail dc=.... from requests
Ext.Loader.setConfig({
    disableCaching : false
});
Ext.Ajax.setConfig({
  disableCaching: false,
  Authorization:
      "Bearer " +
      (localStorage.getItem("bpm_token") || ""),
});
//---set ux path
Ext.Loader.setPath('Ext.ux', globals.base_url+'jscript/ext/src/ux');
//--- this is 4 CodeIgniter smart urls
Ext.apply(Ext.data.AjaxProxy.prototype, {
    noCache: false,
    headers: {
        Authorization:
            "Bearer " + (localStorage.getItem("bpm_token") || ""),
    },
});

Ext.apply(Ext.data.AjaxProxy.prototype.actionMethods, {
    read: 'POST'
});
