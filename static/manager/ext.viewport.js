var modelPanel = Ext.create('Ext.panel.Panel', {
    id: 'modelPanel',
    autoScroll: true,
    listeners: {
        //  render: load_model
    }
});
var caseFreeze = Ext.create('Ext.Action', {
    text: 'Freeze',
    iconCls: 'fa fa-upload',
    handler: function() {
        Ext.Ajax.request({
            // the url to the remote source\/test-call-activity
            url: globals.module_url + 'case_manager/freeze',
            method: 'POST',
            params: {

                'idwf': globals.idwf,
                'idcase': globals.idcase
            },
            // define a handler for request success
            success: function(response, options) {

                var o = JSON.parse(response.responseText);
                Ext.Msg.alert('Status', o.msg);
            },
            // NO errors ! ;)
            failure: function(response, options) {
                alert('Error Loading:' + response.err);
                tree.setLoading(false);

            }
        });
    }
});
var caseUnFreeze = Ext.create('Ext.Action', {
    text: 'UnFreeze',
    iconCls: 'fa fa-download',
    handler: function() {
        Ext.Ajax.request({
            // the url to the remote source\/test-call-activity
            url: globals.module_url + 'case_manager/unfreeze',
            method: 'POST',
            params: {

                'idwf': globals.idwf,
                'idcase': globals.idcase
            },
            // define a handler for request success
            success: function(response, options) {

                var o = JSON.parse(response.responseText);
                if (o.ok) {
                    load_data_callback = function() {
                        tokenStore.load({
                            scope: this,
                            callback: tokens_paint_all
                        });
                    }
                    load_model(globals.idwf);
                    Ext.Msg.alert('Status', o.msg);
                } else {
                    Ext.Msg.alert('Status', o.msg);
                }
            },
            // NO errors ! ;)
            failure: function(response, options) {
                alert('Error Loading:' + response.err);
                tree.setLoading(false);

            }
        });
    }
});
var caseCodeEditor = Ext.create('Ext.Action', {
    text: 'Code Editor',
    iconCls: 'fa fa-code',
    handler: function () {
        openCodeEditor();
    }
});
/**
 * Code Editor window with 3 panes:
 *   - Center top: code editor (source from flat)
 *   - Tbar: Run, Undo, Redo, Save
 *   - Center down: result panel (POST to pybpm-api)
 *   - Right pane: JSONEditor for data
 */
var codeEditorWin = null;
var aceEditor = null;

function openCodeEditor() {
    if (codeEditorWin && codeEditorWin.isVisible()) {
        return codeEditorWin;
    }

    // Build code content from flat dictionary
    var codeContent = '// Code Editor - Model Shapes\n';
    codeContent += '// Source: flat (BPMN shape dictionary)\n\n';
    if (flat && typeof flat === 'object') {
        Ext.Object.each(flat, function(key, shape) {
            codeContent += '// ' + key + '\n';
            codeContent += Ext.JSON.encode(shape, null, 2) + '\n\n';
        });
    } else {
        codeContent += '// No model data loaded yet (flat is empty)';
    }


    // Create the window (like Viewport) — all panels defined inline
    codeEditorWin = Ext.create("Ext.window.Window", {
        title: "Code Editor",
        height: 700,
        width: 900,
        layout: "border",
        items: [{
            // Center panel with border layout (like main viewport center)
            region: 'center',
            margins: '0 0 0 0',
            layout: 'border',
            items: [{
                // South: Result panel (like Token History)
                region: 'south',
                layout: 'fit',
                title: '<i class="icon icon-time" ></i> Result',
                collapsible: true,
                collapsed: false,
                resizable: true,
                animCollapse: false,
                height: 200,
                itemId: 'resultPanel',
                items: [{
                    xtype: 'panel',
                    border: false,
                    html: '<div style="padding:10px;color:#888;">Run code to see results here</div>'
                }]
            }, {
                // Center: Code editor panel (like Case Manager)
                title: 'Code',
                id: 'CodeEditorPanel',
                region: 'center',
                layout: 'fit',
                collapsible: true,
                collapsed: false,
                animCollapse: false,
                resizable: true,
                split: true,
                items: [{
                    xtype: 'panel',
                    border: false,
                    autoScroll: true,
                    html: '<div id="aceCodeEditor" style="width:100%;height:450px;"></div>'
                }],
                tbar: {
                    id: 'CodeEditorTbar',
                    items: [
                        {
                            text: 'Run',
                            iconCls: 'fa fa-play',
                            handler: function () {
                                if (!aceEditor) return;
                                var code = aceEditor.getValue();
                                var resultPanel = Ext.getCmp('resultPanel');
                                if (!resultPanel) return;
                                resultPanel.body.dom.innerHTML = '<div style="padding:10px;color:#888;">Running...</div>';
                                Ext.Ajax.request({
                                    url: globals.apiUrl + '/bpm/test/run_script',
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        'Authorization': 'Bearer ' + (localStorage.getItem('bpm_token') || '')
                                    },
                                    params: { idwf: globals.idwf, idcase: globals.idcase || '' },
                                    jsonData: { code: code },
                                    success: function (response) {
                                        var result = Ext.JSON.decode(response.responseText);
                                        var html = '<div style="padding:10px;font-family:monospace;">';
                                        html += '<div style="color:#0a0;font-weight:bold;">Success</div>';
                                        html += '<pre style="margin:5px 0;background:#f5f5f5;padding:8px;border:1px solid #ddd;">' +
                                                 (result.result || response.responseText) + '</pre></div>';
                                        resultPanel.body.dom.innerHTML = html;
                                    },
                                    failure: function (response) {
                                        var html = '<div style="padding:10px;font-family:monospace;">';
                                        html += '<div style="color:#a00;font-weight:bold;">Error</div>';
                                        html += '<pre style="margin:5px 0;background:#fff5f5;padding:8px;border:1px solid #fcc;">' +
                                                 response.responseText + '</pre></div>';
                                        resultPanel.body.dom.innerHTML = html;
                                    }
                                });
                            }
                        },
                        '-',
                        { text: 'Undo', iconCls: 'fa fa-undo', handler: function () { if (aceEditor) aceEditor.undo(); } },
                        { text: 'Redo', iconCls: 'fa fa-repeat', handler: function () { if (aceEditor) aceEditor.redo(); } },
                        '-',
                        {
                            text: 'Save',
                            iconCls: 'fa fa-save',
                            handler: function () {
                                if (!aceEditor) return;
                                var code = aceEditor.getValue();
                                Ext.Ajax.request({
                                    url: globals.apiUrl + '/bpm/repository/save_script',
                                    method: 'POST',
                                    headers: {
                                        'Content-Type': 'application/json',
                                        'Authorization': 'Bearer ' + (localStorage.getItem('bpm_token') || '')
                                    },
                                    jsonData: { idwf: globals.idwf, code: code },
                                    success: function (response) {
                                        var o = Ext.JSON.decode(response.responseText);
                                        Ext.Msg.alert('Status', o.msg || 'Saved successfully');
                                    },
                                    failure: function (response) {
                                        Ext.Msg.alert('Error', 'Save failed: ' + response.responseText);
                                    }
                                });
                            }
                        },
                    ]
                }
            }]
        }, {
            // East: Data panel (like Cases panel)
            id: 'codeDataPanel',
            region: 'east',
            title: '<i class="icon icon-database"></i> Data',
            animCollapse: true,
            collapsible: true,
            collapsed: true,
            animCollapse: false,
            split: true,
            width: 400,
            minWidth: 300,
            maxWidth: 600,
            margins: '0 0 0 0',
            layout: 'fit',
            items: [{
                xtype: 'panel',
                border: false,
                html: '<div id="jsoneditor-ct" style="width:100%;height:450px;"></div>'
            }]
        }],
        listeners: {
            afterrender: function () {
                // Initialize ACE editor (window is now in DOM)
                Ext.defer(function () {
                    var el = document.getElementById('aceCodeEditor');
                    if (!el) return;
                    if (typeof ace !== 'undefined') {
                        aceEditor = ace.edit(el);
                        aceEditor.setTheme('ace/theme/jsoneditor');
                        aceEditor.session.setMode('ace/mode/javascript');
                        aceEditor.setValue(codeContent, -1);
                        aceEditor.setOptions({
                            fontSize: '13px',
                            showPrintMargin: false,
                            enableBasicAutocompletion: true,
                            enableLiveAutocompletion: true
                        });
                    } else {
                        el.innerHTML = '<textarea id="codeFallback" style="width:100%;height:100%;font-family:monospace;font-size:13px;border:none;resize:none;">' +
                            codeContent.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</textarea>';
                    }
                }, 100);

                // Initialize JSONEditor in the right pane with case process data
                Ext.defer(function () {
                    var container = document.getElementById('jsoneditor-ct');
                    if (!container) return;

                    function initEditor(jsonData) {
                        if (typeof jsonData === 'string') {
                            try { jsonData = Ext.JSON.decode(jsonData); } catch (e) { jsonData = {}; }
                        }
                        if (typeof JSONEditor !== 'undefined') {
                            new JSONEditor(container, {
                                mode: 'tree',
                                modes: ['code', 'form', 'text', 'tree', 'view'],
                                error: function (err) { Ext.Msg.alert('JSON Editor Error', err.toString()); }
                            }, jsonData || {});
                        }
                    }

                    // Case process data (same source as Process Data button), else model shapes
                    if (globals.idcase) {
                        Ext.Ajax.request({
                            url: globals.apiUrl + '/bpm/case_manager/data/' + globals.idwf + '/' + globals.idcase,
                            method: 'GET',
                            success: function (response) { initEditor(response.responseText); },
                            failure: function () { initEditor(flat || {}); }
                        });
                    } else {
                        var jsonData = model_data && model_data.childShapes ? model_data.childShapes : flat;
                        if (typeof jsonData === 'object' && !Array.isArray(jsonData)) {
                            jsonData = { shapes: jsonData };
                        }
                        initEditor(jsonData);
                    }
                }, 300);
            }
        }
    });

    return codeEditorWin.show();
}
Ext.application({
    name: 'AppEditor',
    init: function() {

    },
    launch: function() {
        var remove_loaders = function() {

            Ext.get('loading').remove();
            Ext.fly('loading-mask').remove();
            dgstore.load();

        }

        //----collapse cases panel
        if (globals.idcase) {
            cases_collapsed = true;
        }
        else {
            cases_collapsed = false;
        }
        var center = Ext.create('Ext.Panel', {
            region: 'center',
            margins: '0 0 0 0',
            layout: 'border',
            items: [{
                region: 'south',
                layout: 'fit',
                title: '<i class="icon icon-time" ></i> Token History',
                collapsible: true,
                collapsed: true,
                resizable: true,
                animCollapse: false,
                height: 300,
                items: [tokenGrid]
            }, {
                //title: '<i class="icon icon-bpm"></i> Model Panel / Picker',
                title: '<i class="icon icon-dashboard"></i> Case Manager',
                id: 'ModelPanel',
                region: 'center',
                layout: 'fit',
                collapsible: true,
                collapsed: false,
                animCollapse: false,
                resizable: true,
                split: true,
                items: [modelPanel],
                tbar: {
                    id: 'ModelPanelTbar',
                    disabled: true,
                    items: [
                        TokensPlay,
                        TokensStop,
                        TokensStepBackward,
                        TokensStepForward,
                        TokensTimeSlider,
                        TokensFolow,
                        TokensShowExtras,
                        TokensReload,
                        TokensPaintAll,
                        caseFreeze,
                        caseUnFreeze,
                        caseCodeEditor
                    ]
                }
            }]
        });

        var right = Ext.create('Ext.Panel', {
            id: 'rightPanel',
            region: 'east',
            title: 'Cases',
            animCollapse: true,
            collapsible: true,
            collapsed: cases_collapsed,
            animCollapse: false,
            split: true,
            width: 400, // give east and west regions a width
            minWidth: 300,
            maxWidth: 700,
            margins: '0 0 0 0',
            layout: 'fit',
            items: [mygrid]

        });

        //---CREATE VIEWPORT

        Ext.create('Ext.Viewport', {
            layout: 'border',
            items: [
                center,
                right
            ],
            listeners: {
                render: function() {},
                afterRender: function() {
                    remove_loaders();
                    load_model(globals.idwf);

                }

            }
        });
    }

});
