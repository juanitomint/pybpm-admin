/*
 * RBAC Admin viewport — matches legacy Admin.php layout:
 *   north: title bar
 *   west (260px): Groups dataview
 *   center: TabPanel → Users Grid + Permissions Tree
 *   east (370px): User form panel
 */

Ext.onReady(function () {
  // ============================================================
  // WEST: Groups dataview
  // ============================================================
  var groupStore = Ext.data.StoreManager.lookup("RbacGroupStore");

  var groupTemplate = new Ext.XTemplate(
    '<tpl for=".">',
    '<div class="x-tree-node" id="group-{idgroup}"',
    ' style="padding:4px 6px;cursor:pointer;border-bottom:1px solid #e0e0e0;"',
    ' onmouseover="this.style.background=\'#e8f0fe\'"',
    ' onmouseout="this.style.background=\'transparent\'"',
    '>',
    '  <div style="font-weight:bold">{name}</div>',
    '  <div style="font-size:11px;color:#666">{desc}</div>',
    '</div>',
    '</tpl>',
    '<div class="x-tree-node" style="padding:4px 6px;color:#999;font-style:italic">',
    '  No groups available',
    '</div>'
  );

  var dataview = Ext.create("Ext.dataview.DataView", {
    store: groupStore,
    id: "GroupDataView",
    tpl: groupTemplate,
    itemSelector: "div.x-tree-node",
    emptyText: "No groups available",
    overItemCls: "x-item-over",
    trackOver: true,
    listeners: {
      click: function (dv, index, node, e) {
        var record = dv.store.getAt(index);
        if (record) {
          var idgroup = record.data.idgroup;
          // Load tree and users for this group
          Ext.data.StoreManager.lookup("TreeStore").load({
            params: { idgroup: idgroup },
            callback: function () {
              // Load paths and merge granted status
              Ext.Ajax.request({
                url: globals.apiUrl + "/admin/rbac/paths",
                params: { idgroup: idgroup },
                method: "GET",
                success: function (resp) {
                  var data = Ext.decode(resp.responseText);
                  var paths = data.paths || [];
                  var grantedPaths = {};
                  paths.forEach(function (p) { grantedPaths[p] = true; });
                  var fullTree = Ext.data.StoreManager.lookup("TreeStore");
                  var root = fullTree.getRootNode();
                  if (!root) return;
                  function markGranted(node) {
                    if (node.data.leaf) {
                      node.data.granted = !!grantedPaths[node.data.id];
                    }
                    if (node.childNodes && node.childNodes.length) {
                      node.childNodes.each(markGranted);
                    }
                  }
                  markGranted(root);
                  fullTree.fireEvent("load", fullTree, fullTree.getRange());
                },
              });
            },
          });
          Ext.data.StoreManager.lookup("RbacUserStore").load();
          var userGrid = Ext.getCmp("userGrid");
          if (userGrid) userGrid.getSelectionModel().select(0);
        }
      },
      itemcontextmenu: function (dv, index, node, e) {
        e.preventDefault();
        contextMenu.showAt(e.getXY());
      },
    },
  });

  var left = Ext.create("Ext.Panel", {
    region: "west",
    id: "leftPanel",
    title: "Groups",
    split: true,
    width: 260,
    minWidth: 200,
    maxWidth: 700,
    collapsible: true,
    animCollapse: true,
    margins: "0 0 0 0",
    layout: "fit",
    items: [dataview],
    tbar: [
      {
        text: "Add Group",
        iconCls: "icon-add",
        handler: function () {
          Ext.Msg.prompt("New Group", "Group name:", function (btn, text) {
            if (btn === "ok" && text) {
              Ext.Ajax.request({
                url: globals.apiUrl + "/groups",
                method: "POST",
                jsonData: { name: text, desc: "" },
                success: function () {
                  groupStore.load();
                },
                failure: function () {
                  Ext.Msg.alert("Error", "Failed to create group");
                },
              });
            }
          });
        },
      },
      {
        text: "Remove Group",
        iconCls: "icon-minus-sign",
        handler: function () {
          var sel = groupStore.getSelection();
          if (sel.length === 0) {
            Ext.Msg.alert("Error", "Select a group to remove");
            return;
          }
          var group = sel[0];
          Ext.Msg.confirm(
            "Remove Group",
            "Are you sure you want to remove '" + group.get("name") + "'?",
            function (btn) {
              if (btn === "yes") {
                Ext.Ajax.request({
                  url: globals.apiUrl + "/groups/" + group.get("idgroup"),
                  method: "DELETE",
                  success: function () {
                    groupStore.load();
                    Ext.data.StoreManager.lookup("TreeStore").load();
                  },
                  failure: function () {
                    Ext.Msg.alert("Error", "Failed to delete group");
                  },
                });
              }
            },
          );
        },
      },
    ],
    bbar: {
      items: [
        {
          width: 200,
          xtype: "searchfield",
          store: groupStore,
        },
      ],
    },
  });

  // Context menu for groups
  var contextMenu = Ext.create("Ext.menu.Menu", {
    items: [
      {
        text: "Edit Group",
        handler: function () {
          var sel = groupStore.getSelection();
          if (sel.length === 0) return;
          var group = sel[0];
          var win = Ext.create("Ext.window.Window", {
            title: "Edit Group",
            width: 400,
            modal: true,
            layout: "form",
            items: [
              {
                xtype: "textfield",
                fieldLabel: "Name",
                name: "name",
                value: group.get("name"),
                allowBlank: false,
              },
              {
                xtype: "textarea",
                fieldLabel: "Description",
                name: "desc",
                value: group.get("desc") || "",
                anchor: "100%",
                height: 80,
              },
            ],
            buttons: [
              {
                text: "Save",
                handler: function () {
                  var form = this.up("window").down("form").getForm();
                  if (form.isValid()) {
                    var values = form.getValues();
                    Ext.Ajax.request({
                      url: globals.apiUrl + "/groups/" + group.get("idgroup"),
                      method: "PUT",
                      jsonData: values,
                      success: function () {
                        groupStore.load();
                        win.close();
                      },
                      failure: function () {
                        Ext.Msg.alert("Error", "Failed to update group");
                      },
                    });
                  }
                },
              },
              { text: "Cancel", handler: function () { this.up("window").close(); } },
            ],
          });
          win.show();
        },
      },
    ],
  });

  // ============================================================
  // CENTER: TabPanel → Users Grid + Permissions Tree
  // ============================================================
  var userStore = Ext.data.StoreManager.lookup("RbacUserStore");

  // Check columns for user grid
  var checkLocked = Ext.create("Ext.ux.CheckColumn", {
    header: "Locked",
    dataIndex: "locked",
    width: 60,
    editor: { xtype: "checkbox", cls: "x-grid-checkheader-editor" },
  });
  var checkDisabled = Ext.create("Ext.ux.CheckColumn", {
    header: "Disabled",
    dataIndex: "disabled",
    width: 60,
    editor: { xtype: "checkbox", cls: "x-grid-checkheader-editor" },
  });

  function gridClick(view, record, item, index, e) {
    var form = Ext.getCmp("userForm");
    if (record) {
      form.loadRecord(record);
    }
  }

  var mygrid = Ext.create("Ext.grid.Panel", {
    title: "Users",
    columnLines: true,
    autoScroll: true,
    stripeRows: true,
    id: "userGrid",
    store: userStore,
    columns: [
      { text: "ID", width: 90, dataIndex: "idu", hidden: true, sortable: true },
      { text: "Nick", flex: true, dataIndex: "nick", sortable: true },
      { text: "Name", flex: true, dataIndex: "name", sortable: true },
      { text: "Last Name", dataIndex: "lastname", sortable: true },
      { text: "Email", flex: true, dataIndex: "email", sortable: true },
      checkLocked,
      checkDisabled,
    ],
    viewConfig: {
      listeners: {
        itemclick: gridClick,
      },
    },
    bbar: Ext.create("Ext.PagingToolbar", {
      store: userStore,
      displayInfo: true,
      displayMsg: "Displaying users {0} - {1} of {2}",
      emptyMsg: "No users to display",
      renderTo: mygrid,
    }),
    tbar: [
      {
        xtype: "button",
        text: "Save Changes",
        iconCls: "icon-save",
        handler: function () {
          mygrid.store.sync();
        },
      },
      {
        width: 400,
        xtype: "searchfield",
        store: userStore,
      },
    ],
  });

  // ============================================================
  // Permissions Tree (tab panel item)
  // ============================================================
  var treeStore = Ext.data.StoreManager.lookup("TreeStore");

  var tree = Ext.create("Ext.tree.Panel", {
    id: "PermTree",
    title: "Permissions",
    store: treeStore,
    region: "center",
    expandRoot: true,
    useArrows: true,
    frame: false,
    animate: false,
    stateful: true,
    lines: true,
    layout: "fit",
    columns: [
      {
        xtype: "treecolumn",
        text: "Path",
        flex: 2,
        sortable: true,
        dataIndex: "text",
      },
      {
        text: "Granted",
        flex: 1,
        dataIndex: "granted",
        sortable: true,
      },
    ],
    listeners: {
      checkchange: function (node, checked) {
        node.expand();
        node.eachChild(function (child) {
          child.set("checked", checked);
          if (child.childNodes.length) {
            checkchange(child, checked);
          }
        });
      },
    },
    tbar: [
      {
        text: "Expand All",
        handler: function () {
          tree.expandAll();
        },
      },
      {
        text: "Collapse All",
        handler: function () {
          tree.collapseAll();
        },
      },
      {
        text: "Save",
        iconCls: "icon-save",
        handler: function () {
          var records = tree.getView().getChecked();
          var paths = [];
          Ext.Array.each(records, function (rec) {
            paths.push(rec.data.id);
          });
          var sel = groupStore.getSelection();
          if (sel.length === 0) {
            Ext.Msg.alert("Error", "Select a group first");
            return;
          }
          var idgroup = sel[0].get("idgroup");
          tree.setLoading("Saving");
          Ext.Ajax.request({
            url: globals.apiUrl + "/rbac/repository",
            method: "PUT",
            params: { idgroup: idgroup, paths: paths.join(",") },
            success: function () {
              tree.setLoading(false);
            },
            failure: function () {
              tree.setLoading(false);
              Ext.Msg.alert("Error", "Failed to save permissions");
            },
          });
        },
      },
      {
        text: "Reload",
        handler: function () {
          Ext.data.StoreManager.lookup("TreeStore").load();
          tree.uncheck_all();
        },
      },
    ],
  });

  // Helper functions for tree
  function checkchange(node, checked) {
    node.expand();
    node.eachChild(function (n) {
      n.set("checked", checked);
      if (n.childNodes.length) {
        checkchange(n, checked);
      }
    });
  }
  tree.uncheck_all = function () {
    var root = tree.store.tree.getRootNode();
    if (root) {
      root.set("checked", false);
      checkchange(root, false);
    }
  };

  var centerPanel = Ext.create("Ext.Panel", {
    region: "center",
    id: "centerPanel",
    layout: "fit",
    margins: "0 0 0 0",
    items: {
      xtype: "tabpanel",
      id: "mainTabPanel",
      activeTab: 0,
      items: [mygrid, tree],
      listeners: {
        tabchange: function (tabpanel, tab) {
          if (tab.id === "PermTree") {
            Ext.data.StoreManager.lookup("TreeStore").load();
          }
        },
      },
    },
  });

  // ============================================================
  // EAST: User form panel
  // ============================================================
  var required = '<span style="color:red;font-weight:bold">*</span>';

  var userForm = Ext.create("Ext.form.Panel", {
    id: "userForm",
    region: "east",
    title: "User Details",
    width: 370,
    minWidth: 0,
    maxWidth: 450,
    split: true,
    collapsible: true,
    margins: "0 0 0 0",
    layout: "form",
    bodyPadding: "5 5 0",
    frame: false,
    autoScroll: true,
    items: [
      {
        xtype: "fieldset",
        title: "User Information",
        defaultType: "textfield",
        collapsible: true,
        layout: "anchor",
        defaults: { anchor: "100%" },
        items: [
          { fieldLabel: "ID", name: "idu", readOnly: true },
          { fieldLabel: "First Name", afterLabelTextTpl: required, name: "name", allowBlank: false },
          { fieldLabel: "Last Name", afterLabelTextTpl: required, name: "lastname", allowBlank: false },
          { fieldLabel: "Company", name: "company" },
          { fieldLabel: "Email", afterLabelTextTpl: required, name: "email", vtype: "email" },
          { fieldLabel: "ID Number", afterLabelTextTpl: required, name: "idnumber" },
          { fieldLabel: "Phone", name: "phone" },
          { fieldLabel: "Nick", name: "nick" },
          { fieldLabel: "Signature", name: "signature", xtype: "textareafield", grow: true },
          { fieldLabel: "Password", name: "passw", inputType: "password" },
          { fieldLabel: "Repeat Password", name: "password2", inputType: "password" },
        ],
      },
      {
        xtype: "fieldset",
        title: "Groups / Roles",
        collapsible: true,
        layout: "anchor",
        defaults: { anchor: "100%" },
        items: [
          {
            id: "groupField",
            labelAlign: "top",
            fieldLabel: "Groups",
            name: "group",
          },
          {
            xtype: "container",
            layout: "hbox",
            items: [
              {
                xtype: "combo",
                id: "groupCombo",
                store: groupStore,
                displayField: "name",
                valueField: "idgroup",
                hideLabel: true,
                anchor: "100%",
                listConfig: {
                  loadingText: "Searching...",
                  emptyText: "No matching Groups found.",
                },
              },
              {
                xtype: "button",
                text: "Add",
                iconCls: "icon-add",
                handler: function () {
                  var combo = Ext.getCmp("groupCombo");
                  if (combo.getValue()) {
                    var gf = Ext.getCmp("groupField");
                    var groups = gf.getValue() ? gf.getValue().split(",") : [];
                    if (groups.indexOf(combo.getValue().toString()) === -1) {
                      groups.push(combo.getValue());
                      gf.setValue(groups.join(","));
                    }
                  }
                },
              },
            ],
          },
          {
            xtype: "container",
            items: [
              Ext.create("Ext.grid.Panel", {
                id: "UserGroupGrid",
                store: Ext.data.StoreManager.lookup("UserGroupStore"),
                title: "Assigned Groups",
                stateful: true,
                collapsible: true,
                multiSelect: true,
                columns: [
                  {
                    xtype: "actioncolumn",
                    width: 50,
                    items: [
                      {
                        iconCls: "icon-remove",
                        tooltip: "Remove from group",
                        handler: function (grid, rowIndex) {
                          var rec = grid.store.getAt(rowIndex);
                          Ext.Msg.confirm(
                            "Confirm",
                            "Remove " + rec.get("name") + "?",
                            function (btn) {
                              if (btn === "yes") {
                                grid.store.remove(rec);
                                var gf = Ext.getCmp("groupField");
                                var groups = gf.getValue() ? gf.getValue().split(",") : [];
                                groups = groups.filter(function (g) { return g !== rec.get("idgroup"); });
                                gf.setValue(groups.join(","));
                              }
                            },
                          );
                        },
                      },
                    ],
                  },
                  { text: "ID", dataIndex: "idgroup", width: 60 },
                  { text: "Name", dataIndex: "name", flex: 1 },
                ],
              }),
            ],
          },
        ],
      },
    ],
    buttons: [
      {
        text: "Remove User",
        iconCls: "icon-remove",
        handler: function () {
          var grid = Ext.getCmp("userGrid");
          var sel = grid.getSelectionModel().getSelection();
          if (sel.length > 0) {
            Ext.Msg.confirm(
              "Remove User",
              "Remove user '" + sel[0].get("nick") + "'?",
              function (btn) {
                if (btn === "yes") {
                  Ext.Ajax.request({
                    url: globals.apiUrl + "/users/" + sel[0].get("idu"),
                    method: "DELETE",
                    success: function () {
                      grid.store.remove(sel[0]);
                      grid.store.sync();
                      Ext.getCmp("userForm").getForm().reset();
                    },
                    failure: function () {
                      Ext.Msg.alert("Error", "Failed to delete user");
                    },
                  });
                }
              },
            );
          }
        },
      },
      {
        text: "Reset",
        iconCls: "icon-refresh",
        handler: function () {
          Ext.getCmp("userForm").getForm().reset();
        },
      },
      {
        text: "Save",
        iconCls: "icon-save",
        handler: function () {
          var form = Ext.getCmp("userForm").getForm();
          var values = form.getValues();
          if (!values.idu) {
            // New user
            Ext.Ajax.request({
              url: globals.apiUrl + "/users",
              method: "POST",
              jsonData: {
                nick: values.nick,
                name: values.name,
                lastname: values.lastname,
                email: values.email,
                idgroup: null,
              },
              success: function (resp) {
                var data = Ext.decode(resp.responseText);
                form.setValues(data);
                groupStore.load();
                Ext.Msg.alert("Success", "User created");
              },
              failure: function () {
                Ext.Msg.alert("Error", "Failed to create user");
              },
            });
          } else {
            // Update existing user
            Ext.Ajax.request({
              url: globals.apiUrl + "/users/" + values.idu,
              method: "PUT",
              jsonData: {
                name: values.name,
                lastname: values.lastname,
                email: values.email,
              },
              success: function () {
                Ext.Msg.alert("Success", "User updated");
                userStore.load();
              },
              failure: function () {
                Ext.Msg.alert("Error", "Failed to update user");
              },
            });
          }
        },
      },
    ],
  });

  var right = Ext.create("Ext.Panel", {
    region: "east",
    id: "rightPanel",
    layout: "fit",
    margins: "0 0 0 0",
    items: [userForm],
  });

  // ============================================================
  // Viewport
  // ============================================================
  Ext.create("Ext.container.Viewport", {
    layout: "border",
    items: [
      {
        region: "north",
        html: '<div style="padding:8px 12px;font-size:14px;font-weight:bold;"><i class="icon icon-group"></i> RBAC Group &amp; User Manager</div>',
        collapsible: false,
        height: 36,
      },
      left,
      centerPanel,
      right,
    ],
    listeners: {
      afterrender: function () {
        Ext.data.StoreManager.lookup("RbacGroupStore").clearFilter();
        Ext.data.StoreManager.lookup("TreeStore").load();
      },
    },
  });

  // Remove loading mask
  Ext.get("loading-mask").remove();
  Ext.get("loading").remove();
});
