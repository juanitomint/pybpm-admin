/*
 *                      GROUPS
 */
Ext.define("Group", {
  extend: "Ext.data.Model",
  idProperty: "idgroup",
  fields: [
    "idgroup",
    "name",
    "desc",
    {
      name: "disabled",
      type: "bool",
    },
    "users",
  ],
});

Ext.create("Ext.data.Store", {
  id: "GroupStore",
  model: "Group",
  autoLoad: false,
  proxy: {
    type: "rest",
    url: globals.apiUrl + "/groups",
    headers: {
      Authorization: "Bearer " + (localStorage.getItem("bpm_token") || ""),
    },
    reader: {
      type: "json",
      root: "rows",
      totalProperty: "totalCount",
    },
    writer: {
      type: "json",
    },
  },
  sorters: [
    {
      property: "idgroup",
      direction: "ASC",
    },
  ],
  listeners: {
    // load: onGroupStoreLoad
  },
});

function onGroupStoreLoad() {
  //---select first group in list.
  dataview.selModel.select(0);
}
/*
 *                      USERS
 */
Ext.define("User", {
  extend: "Ext.data.Model",
  idProperty: "idu",
  fields: [
    "_id",
    "idu",
    "nick",
    "name",
    "lastname",
    "email",
    "phone",
    "idnumber",
    "group",
    "signature",
    {
      name: "locked",
      type: "bool",
    },
    {
      name: "disabled",
      type: "bool",
    },
  ],
});

Ext.create("Ext.data.Store", {
  id: "UserStore",
  model: "User",
  pageSize: 50,
  autoLoad: false,
  proxy: {
    type: "rest",
    url: globals.apiUrl + "/users",
    headers: {
      Authorization: "Bearer " + (localStorage.getItem("bpm_token") || ""),
    },
    reader: {
      type: "json",
    },
  },
  sorters: [
    {
      property: "idu",
      direction: "ASC",
    },
  ],
});
/*
 *    Empty store for user groups
 */

Ext.create("Ext.data.Store", {
  id: "UserGroupStore",
  model: "Group",
  sorters: [
    {
      property: "name",
      direction: "ASC",
    },
  ],
});
/*
 *      Tree Store
 */

function onTreeStoreLoad() {
  // tree.load_checked();
}
Ext.create("Ext.data.TreeStore", {
  id: "TreeStore",
  autoLoad: false,
  proxy: {
    type: "rest",
    noCache: false, //---get rid of the ?dc=.... in urls
    url: globals.apiUrl + "/rbac/repository",
    headers: {
      Authorization: "Bearer " + (localStorage.getItem("bpm_token") || ""),
    },
  },
  sorters: [
    {
      property: "leaf",
      direction: "ASC",
    },
    {
      property: "text",
      direction: "ASC",
    },
  ],
  listeners: {
    load: onTreeStoreLoad,
  },
});
