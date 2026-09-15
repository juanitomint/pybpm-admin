/*
 * RBAC data stores — proxy to pybpm-api endpoints.
 * pybpm-api returns plain arrays for /groups and /users,
 * and {"tree": [...]} for /admin/rbac/repository.
 */

/*
 *  GROUPS
 */
Ext.define("RbacGroup", {
  extend: "Ext.data.Model",
  fields: [
    "idgroup",
    "name",
    "desc",
    { name: "disabled", type: "bool" },
  ],
});

Ext.create("Ext.data.Store", {
  id: "RbacGroupStore",
  model: "RbacGroup",
  autoLoad: true,
  proxy: {
    type: "ajax",
    noCache: false,
    method: "GET",
    url: globals.apiUrl + "/groups",
    reader: {
      type: "json",
      root: "",  // plain array response
    },
  },
  sorters: [{ property: "idgroup", direction: "ASC" }],
  listeners: {
    load: function () {
      // Select first group on load
      var grid = Ext.getCmp("GroupGrid");
      if (grid && this.getCount() > 0) {
        grid.getSelectionModel().select(0);
      }
    },
  },
});

/*
 *  USERS
 */
Ext.define("RbacUser", {
  extend: "Ext.data.Model",
  fields: [
    "idu",
    "nick",
    "name",
    "lastname",
    "email",
    "idgroup",
    { name: "locked", type: "bool" },
    { name: "disabled", type: "bool" },
  ],
});

Ext.create("Ext.data.Store", {
  id: "RbacUserStore",
  model: "RbacUser",
  pageSize: 50,
  autoLoad: false,
  proxy: {
    type: "ajax",
    noCache: false,
    method: "GET",
    url: globals.apiUrl + "/users",
    reader: {
      type: "json",
      root: "",  // plain array response
    },
    writer: {
      type: "json",
    },
  },
  sorters: [{ property: "idu", direction: "ASC" }],
});

/*
 *  PERMISSION TREE
 */
Ext.create("Ext.data.TreeStore", {
  id: "RbacTreeStore",
  autoLoad: false,
  proxy: {
    type: "ajax",
    method: "GET",
    noCache: false,
    url: globals.apiUrl + "/admin/rbac/repository",
    reader: {
      type: "json",
      root: "tree",  // response is {"tree": [...]}
    },
  },
  sorters: [
    { property: "text", direction: "ASC" },
  ],
  listeners: {
    load: function (tree, records) {
      // Expand root after load
      var root = tree.getRootNode();
      if (root) {
        root.expand();
      }
    },
  },
});
/*
 *  PATHS LIST (for RBAC tree management)
 */
Ext.create("Ext.data.Store", {
  id: "RbacPathsStore",
  autoLoad: false,
  proxy: {
    type: "ajax",
    method: "GET",
    noCache: false,
    url: globals.apiUrl + "/admin/rbac/paths",
    reader: {
      type: "json",
      root: "paths",  // response is {"paths": [...]}
    },
  },
});
