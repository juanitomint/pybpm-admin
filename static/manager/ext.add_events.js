/*
 *  Add events for overlays
 */
var add_events = function(shapes) {
    for (j in shapes) {
        var shape = shapes[j];
        xBound = 0;
        yBound = 0;
        //console.log(shape.stencil.id,exclude_shape.indexOf(shape.stencil.id)==-1);
        xBound = shape.bounds.upperLeft.x + offset_x; //( -1 to fix nested objects
        yBound = shape.bounds.upperLeft.y + offset_y;
        width = shape.bounds.lowerRight.x - shape.bounds.upperLeft.x;
        height = shape.bounds.lowerRight.y - shape.bounds.upperLeft.y
        if (exclude_shape.indexOf(shape.stencil.id) == -1) { //---if not excluded
            switch (shape.stencil.id) {
                case 'Lane':
                    width = 24;
                    break;

            }
            add = new Array();
            var buttons = [];
            add.push('<span class="resourceId">resourceId:<br>' + shape.resourceId + '</span>');
            if (shape.properties.tasktype) {
                switch (shape.properties.tasktype) {
                    case 'Script':
                        if (globals.idcase) {
                            (function(s) {
                                buttons.push({
                                    xtype: 'button',
                                    text: '<i class="fa fa-flask"></i> Test Script',
                                    cls: 'x-btn-text-icon',
                                    tooltip: 'Open Code Editor for this task',
                                    handler: function () {
                                        openCodeEditorForShape(s);
                                    }
                                });
                            })(shape);
                        }
                        break;

                    case 'Send':
                        if (globals.idcase) {
                            (function(s) {
                                buttons.push({
                                    xtype: 'button',
                                    text: '<i class="fa fa-envelope"></i> Test Msg',
                                    cls: 'x-btn-text-icon',
                                    tooltip: 'Open Code Editor for this task',
                                    handler: function () {
                                        openCodeEditorForShape(s);
                                    }
                                });
                            })(shape);
                        }
                        break;

                }
            }

            Ext.core.DomHelper.append('svg-box', {
                tag: 'div',
                cls: 'model_overlay',
                id: 'overlay' + shape.resourceId,
                style: ' border-radius: 3px;\n\
                        position:absolute;\n\
                        left:' + xBound + 'px;\n\
                        top:' + yBound + 'px;\n\
                        width:' + width + 'px;\n\
                        height:' + height + 'px;\n\
\n\
'
            });
            config = {
                id: 'toolTip' + shape.resourceId,
                target: 'overlay' + shape.resourceId,
                anchor: 'bottom',
                dismissDelay: 0,
                minWidth: 320,
                //anchorOffset: 85, // center the anchor on the tooltip
                items: [
                    { xtype: 'container', html: add.join('<br/>') },
                    { xtype: 'container', html: '<br/>' },
                    { xtype: 'container', layout: 'hbox', items: buttons }
                ]
            };
            tooltips.push(
                Ext.create('Ext.tip.ToolTip', config)
            );

            div = Ext.get('overlay' + shape.resourceId);
            /*
            div.on('mouseover',function(event,target,options){
                this.dom.style.setProperty('background-color','green');
                this.dom.style.setProperty('opacity','0.5');
            });
            div.on('mouseout',function(event,target,options){
                this.dom.style.removeProperty('background-color');
                this.dom.style.removeProperty('opacity');
            });
            */
            div.on('click', function(event, target, options) {
                resourceId = target.id.replace('overlay', '');
                tip = Ext.getCmp('toolTip' + resourceId);
                if (tip.isVisible()) {
                    Ext.getCmp('toolTip' + resourceId).autoHide = true;
                }
                else {
                    Ext.getCmp('toolTip' + resourceId).show();
                    Ext.getCmp('toolTip' + resourceId).autoHide = false;
                }
                //console.log(resourceId);
                tokenGrid.selModel.select(tokenGrid.store.find('resourceId', resourceId));
            });
        }
        flat[shape.resourceId] = shape;
        if (shape.childShapes.length) {
            var offset_x_orig = offset_x;
            var offset_y_orig = offset_y;
            offset_x = xBound;
            offset_y = yBound;
            add_events(shape.childShapes);
            //---restore original valoues of offset
            offset_x = offset_x_orig;
            offset_y = offset_y_orig;

        }
    }
}
/**
 * Open Code Editor focused on a specific shape's code.
 * @param {Object} shape - The BPMN shape object from flat
 */
function openCodeEditorForShape(shape) {
    if (!codeEditorWin || !codeEditorWin.isVisible()) {
        openCodeEditor();
    }

    // Script content from flat[resourceId].properties.script
    var codeContent = (shape.properties && typeof shape.properties.script === 'string') ? shape.properties.script : '';

    function setEditorValue() {
        if (typeof aceEditor !== 'undefined' && aceEditor) {
            aceEditor.setValue(codeContent, -1);
            return true;
        }
        // Textarea fallback (ACE not loaded)
        var el = document.getElementById('aceCodeEditor');
        var ta = el && (el.querySelector('textarea') || document.getElementById('codeFallback'));
        if (ta) { ta.value = codeContent; return true; }
        return false;
    }

    // ACE initializes ~100ms after window render; poll until ready so the
    // initial all-shapes content doesn't overwrite this shape's script.
    var tries = 0;
    (function attempt() {
        if (setEditorValue()) return;
        if (++tries < 20) Ext.defer(attempt, 100);
    })();

    // Expand the window if needed
    if (codeEditorWin.getHeight() < 500) {
        codeEditorWin.setSize(900, 700);
    }
    codeEditorWin.center();
}