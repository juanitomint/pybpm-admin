/*
 *  This file defines all data stores used in the app
 *
 */


/*
 *                      GROUPS
 */
Ext.define('Group', {
    extend: 'Ext.data.Model',
    fields: [
    'idgroup',
    'name',
    'desc',
    {
        name: 'disabled',
        type: 'bool'
    },
    'users'
    ]
});


Ext.create('Ext.data.Store', {
    id:'GroupStore',
    model: 'Group',
    autoLoad: false,
    proxy: {
        type: 'ajax',
        noCache: false,//---get rid of the ?dc=.... in urls
        method:'post',
        api: {
            create  : globals.apiUrl+'admin/group/create',
            read    : globals.apiUrl+'admin/group/read',
            update  : globals.apiUrl+'admin/group/update',
            destroy : globals.apiUrl+'admin/group/destroy'
        },
        reader: {
            type: 'json',
            root: 'rows',
            totalProperty: 'totalCount'
        },
        writer: {
            type: 'json'
        }
    },
    sorters: [{
        property: 'idgroup',
        direction: 'ASC'
    }]
    ,
    listeners:{
        load: onGroupStoreLoad
    }

});

function onGroupStoreLoad(){
    //---select first group in list.
    dataview.selModel.select(0)
}
/*
 *                      USERS
 */
Ext.define('User', {
    extend: 'Ext.data.Model',
    fields: [
    'idu',
    'nick',
    'name',
    'lastname',
    'email',
    'phone',
    'idnumber',
    'group',
    {
        name: 'locked',
        type: 'bool'
    },
    {
        name: 'disabled',
        type: 'bool'
    }
    ]
});


Ext.create('Ext.data.Store', {
    id:'ModelStore',
    model: 'User',
    pageSize: 50,
    autoLoad: false,
    proxy: {
        type: 'ajax',
        noCache: false,//---get rid of the ?dc=.... in urls
        method:'post',
        api: {
            create  : globals.apiUrl+'repository/model/create',
            read    : globals.apiUrl+'repository/model/read',
            update  : globals.apiUrl+'admin/user/model/update',
            destroy : globals.apiUrl+'admin/user/model/destroy'
        },
        reader: {
            type: 'json',
            root: 'rows',
            totalProperty: 'totalCount'
        },
        writer: {
            type: 'json'
        }
    },
    sorters: [{
        property: 'idu',
        direction: 'ASC'
    }]
});
/*
 *    Empty store for user groups
 */

Ext.create('Ext.data.Store', {
    id:'UserGroupStore',
    model: 'Group',
    sorters: [{
        property: 'name',
        direction: 'ASC'
    }]
});
/*
 *      Tree Store
 */

function onTreeStoreLoad(){
//tree.load_checked(dataview.selModel.getLastSelected().data.idgroup);
}
Ext.create('Ext.data.TreeStore', {
    id:"TreeStore",
    autoLoad: false,
    proxy: {
        type: 'ajax',
        noCache: false,//---get rid of the ?dc=.... in urls
        url: globals.apiUrl +'bpm/repository/'+ 'get_tree2/json',
        headers: {
            'Authorization': 'Bearer ' + (localStorage.getItem('bpm_token') || '')
        }
    //url:'http://localhost/ext/examples/build/KitchenSink/ext-theme-neptune/resources/data/tree/check-nodes.json?_dc=1363724048632&sort=[{%22property%22%3A%22leaf%22%2C%22direction%22%3A%22ASC%22}%2C{%22property%22%3A%22text%22%2C%22direction%22%3A%22ASC%22}]&node=root'
    },
    sorters: [{
        property: 'leaf',
        direction: 'ASC'
    }, {
        property: 'text',
        direction: 'ASC'
    }],
    listeners:{
//load: onTreeStoreLoad
}

});
