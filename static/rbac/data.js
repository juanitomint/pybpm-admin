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
    url: globals.apiUrl + "/rbac/repository",
    headers: {
      Authorization: "Bearer " + (localStorage.getItem("bpm_token") || ""),
    },
    reader: {
      type: "json",
      root: "data",
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

Ext.create("Ext.data.TreeStore", {
  id: "TreeMock",
  root: {
    expanded: true,
    children: [
      {
        id: "root\/modules",
        text: "modules",
        leaf: false,
        checked: false,
        expanded: false,
        children: [
          {
            id: "root\/modules\/dashboard",
            text: "dashboard",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/dashboard\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/dashboard\/controllers\/dashboard",
                    text: "dashboard",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/dashboard\/controllers\/dashboard\/index",
                        text: "index",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-18 12:19:12",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/dashboard\/controllers\/dashboard\/tasks",
                        text: "tasks",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-03 01:42:18",
                          idu: 1,
                        },
                      },
                    ],
                  },
                  {
                    id: "root\/modules\/dashboard\/controllers\/alerts",
                    text: "alerts",
                    leaf: true,
                    checked: false,
                    iconCls: "dot-green",
                    data: {
                      source: "AutoDiscovery",
                      checkdate: "2026-09-18 12:19:12",
                      idu: 1,
                    },
                  },
                ],
              },
            ],
          },
          {
            id: "root\/modules\/gitmod",
            text: "gitmod",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/gitmod\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/gitmod\/controllers\/gitmod",
                    text: "gitmod",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/gitmod\/controllers\/gitmod\/tile",
                        text: "tile",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-18 12:19:12",
                          idu: 1,
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            id: "root\/modules\/menu",
            text: "menu",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/menu\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/menu\/controllers\/menu",
                    text: "menu",
                    leaf: true,
                    checked: false,
                    iconCls: "dot-green",
                    data: {
                      source: "AutoDiscovery",
                      checkdate: "2026-09-18 12:19:12",
                      idu: 1,
                    },
                  },
                ],
              },
            ],
          },
          {
            id: "root\/modules\/user",
            text: "user",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/user\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/user\/controllers\/profile",
                    text: "profile",
                    leaf: true,
                    checked: false,
                    iconCls: "dot-green",
                    data: {
                      source: "AutoDiscovery",
                      checkdate: "2026-09-18 12:19:12",
                      idu: 1,
                    },
                  },
                  {
                    id: "root\/modules\/user\/controllers\/admin",
                    text: "admin",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/user\/controllers\/admin\/index",
                        text: "index",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-17 02:45:42",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/user\/controllers\/admin\/group",
                        text: "group",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-17 02:45:42",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/user\/controllers\/admin\/user",
                        text: "user",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-15 02:12:32",
                          idu: 1,
                        },
                      },
                    ],
                  },
                  {
                    id: "root\/modules\/user\/controllers\/rbac_admin",
                    text: "rbac_admin",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/user\/controllers\/rbac_admin\/repository",
                        text: "repository",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-18 12:19:51",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/user\/controllers\/rbac_admin\/getpaths",
                        text: "getpaths",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-09-15 02:12:32",
                          idu: 1,
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
          {
            id: "root\/modules\/inbox",
            text: "inbox",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/inbox\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/inbox\/controllers\/inbox",
                    text: "inbox",
                    leaf: true,
                    checked: false,
                    iconCls: "dot-green",
                    data: {
                      source: "AutoDiscovery",
                      checkdate: "2026-09-18 12:19:12",
                      idu: 1,
                    },
                  },
                ],
              },
            ],
          },
          {
            id: "root\/modules\/bpm",
            text: "bpm",
            leaf: false,
            checked: false,
            expanded: false,
            children: [
              {
                id: "root\/modules\/bpm\/controllers",
                text: "controllers",
                leaf: false,
                checked: false,
                expanded: false,
                children: [
                  {
                    id: "root\/modules\/bpm\/controllers\/admin",
                    text: "admin",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/bpm\/controllers\/admin\/index",
                        text: "index",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 23:16:31",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/admin\/get_tree2",
                        text: "get_tree2",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 23:16:32",
                          idu: 1,
                        },
                      },
                    ],
                  },
                  {
                    id: "root\/modules\/bpm\/controllers\/repository",
                    text: "repository",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/add",
                        text: "add",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-01 23:24:18",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/svg",
                        text: "svg",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 23:16:36",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/load",
                        text: "load",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 23:16:38",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/save",
                        text: "save",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-02 00:21:16",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/duplicate",
                        text: "duplicate",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-01 23:21:39",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/delete",
                        text: "delete",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-01 23:21:32",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/import_test",
                        text: "import_test",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-03 01:40:15",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/repository\/import",
                        text: "import",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-03 02:08:09",
                          idu: 1,
                        },
                      },
                    ],
                  },
                  {
                    id: "root\/modules\/bpm\/controllers\/case_manager",
                    text: "case_manager",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/bpm\/controllers\/case_manager\/browse",
                        text: "browse",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 20:49:14",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/case_manager\/data",
                        text: "data",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 20:49:28",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/case_manager\/tokens",
                        text: "tokens",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 20:49:33",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/case_manager\/revert",
                        text: "revert",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-11 23:57:34",
                          idu: 1,
                        },
                      },
                    ],
                  },
                  {
                    id: "root\/modules\/bpm\/controllers\/engine",
                    text: "engine",
                    leaf: false,
                    checked: false,
                    expanded: false,
                    children: [
                      {
                        id: "root\/modules\/bpm\/controllers\/engine\/newcase",
                        text: "newcase",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 20:48:52",
                          idu: 1,
                        },
                      },
                      {
                        id: "root\/modules\/bpm\/controllers\/engine\/run",
                        text: "run",
                        leaf: true,
                        checked: false,
                        iconCls: "dot-green",
                        data: {
                          source: "AutoDiscovery",
                          checkdate: "2026-08-14 20:48:52",
                          idu: 1,
                        },
                      },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
});
