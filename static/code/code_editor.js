/**
 * Code Editor — standalone script editor for BPMN task type scripts.
 *
 * Loads the script property from a model shape via /code/{idwf}/{case_id}/{resource_id},
 * initializes an ACE editor with the appropriate language mode, and provides:
 *   - Run button to execute via /code/execute (morty sandbox)
 *   - Refresh Data to fetch case data from /code/data/{idwf}/{case_id}
 *   - Live JSON data pane showing the data object
 */
(function () {
    "use strict";

    var ctx = window.__EDITOR_CTX;
    if (!ctx) {
        document.body.innerHTML = '<p style="color:#f44;padding:20px">Missing editor context.</p>';
        return;
    }

    var idwf = ctx.idwf;
    var caseId = ctx.case_id;
    var shapeId = ctx.resource_id;

    var editor = null;
    var currentLanguage = "python";
    var currentData = null;

    /* ---- Helpers ---- */

    function setStatus(msg, ok) {
        var el = document.getElementById("status");
        el.textContent = msg;
        el.className = "status " + (ok ? "ok" : "err");
    }

    function hideLoading() {
        document.getElementById("loading").classList.add("hidden");
    }

    function loadAceMode(modeName) {
        return new Promise(function (resolve, reject) {

            // CDN fallback for mode loading
            var script = document.createElement("script");


            script.src = "https://cdnjs.cloudflare.com/ajax/libs/ace/1.44.0/src-noconflict/mode-" + modeName + ".js";
            script.onload = resolve;
            script.onerror = function() {
                // Fallback to text mode on CDN failure
                console.warn("Failed to load ACE mode: " + modeName + ", using text mode");
                resolve();
            };
            document.head.appendChild(script);
        });
    }

    function loadAceTheme(themeName) {
        return new Promise(function (resolve, reject) {
            if (typeof ace.require === "function") {
                try {
                    ace.require("ace/theme/" + themeName);
                    resolve();
                    return;
                } catch (e) { /* fall through */ }
            }
            var script = document.createElement("script");

            script.src = "/static/jscript/ace-builds/src-noconflict/theme-" + themeName + ".js";
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    function mapLanguageToAceMode(lang) {
        var map = {
            php: "php",
            python: "python",
            javascript: "javascript",
            js: "javascript",
            java: "java",
            c_cpp: "c_cpp",
            cpp: "c_cpp",
            c: "c_cpp",
            css: "css",
            html: "html",
            xml: "xml",
            json: "json",
            sql: "sql",
            ruby: "ruby",
            rb: "ruby",
            lua: "lua",
            perl: "perl",
            shell: "sh",
            bash: "sh",
            typescript: "typescript",
            ts: "typescript",
            groovy: "groovy",
            kotlin: "kotlin",
            swift: "swift",
            go: "go",
            rust: "rust",
            r: "r",
            scala: "scala",
            dart: "dart",
            yaml: "yaml",
            yml: "yaml",
            markdown: "markdown",
            text: "text",
        };
        return map[lang.toLowerCase()] || "text";
    }

    function mapLanguageToMortyLang(lang) {
        var map = {
            php: "php",
            python: "python",
            javascript: "javascript",
            js: "javascript",
            java: "java",
            c_cpp: "c",
            cpp: "c++",
            c: "c",
            ruby: "ruby",
            rb: "ruby",
            lua: "lua",
            perl: "perl",
            shell: "shell",
            bash: "shell",
            typescript: "typescript",
            ts: "typescript",
            groovy: "groovy",
            kotlin: "kotlin",
            swift: "swift",
            go: "go",
            rust: "rust",
            r: "r",
            scala: "scala",
            dart: "dart",
            yaml: "yaml",
            yml: "yaml",
            markdown: "markdown",
            text: "plaintext",
        };
        return map[lang.toLowerCase()] || "python";
    }

    function syntaxHighlightJSON(obj) {
        var json = JSON.stringify(obj, null, 2);
        return json
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(
                /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
                function (match) {
                    var cls = "number";
                    if (/^"/.test(match)) {
                        cls = /:$/.test(match) ? "key" : "string";
                    } else if (/true|false/.test(match)) {
                        cls = "bool";
                    } else if (/null/.test(match)) {
                        cls = "null";
                    }
                    return '<span class="' + cls + '">' + match + "</span>";
                }
            );
    }

    /* ---- API calls ---- */

    async function fetchShapeData() {
        var url = "/code/" + idwf + "/" + caseId + "/" + shapeId;
        var resp = await fetch(url);
        if (!resp.ok) {
            var err = await resp.json().catch(function () { return { error: resp.statusText }; });
            throw new Error("Failed to fetch shape data: " + (err.error || resp.statusText));
        }
        return resp.json();
    }

    async function fetchCaseData() {
        var url = "/code/data/" + idwf + "/" + caseId;
        var resp = await fetch(url);
        if (!resp.ok) {
            var err = await resp.json().catch(function () { return { error: resp.statusText }; });
            setStatus("Data fetch failed: " + (err.error || resp.statusText), false);
            return null;
        }
        return resp.json();
    }

    async function executeScript(script, language, data) {
        var resp = await fetch("/code/execute", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                language: language,
                script: script,
                data: data,
            }),
        });
        if (!resp.ok) {
            var err = await resp.json().catch(function () { return { error: resp.statusText }; });
            return { output: null, data: null, error: err.error || resp.statusText };
        }
        return resp.json();
    }

    /* ---- UI setup ---- */

    function initLanguageSelector(shapeData) {
        var select = document.getElementById("lang-select");
        var defaultLang = shapeData.script_language || "python";

        var languages = [
            "php",
            "python",
            "javascript",
            "java",
            "c_cpp",
            "ruby",
            "lua",
            "perl",
            "shell",
            "typescript",
            "groovy",
            "kotlin",
            "go",
            "rust",
            "r",
            "scala",
            "text",
        ];

        select.innerHTML = "";
        languages.forEach(function (lang) {
            var opt = document.createElement("option");
            opt.value = lang;
            opt.textContent = lang;
            if (lang === defaultLang) opt.selected = true;
            select.appendChild(opt);
        });

        currentLanguage = select.value;
        select.addEventListener("change", function () {
            currentLanguage = this.value;
        });
    }

    function initEditor(shapeData) {
        editor = ace.edit("editor");
        editor.setTheme("ace/theme/chrome");
        editor.session.setMode("ace/mode/" + currentLanguage);
        editor.setFontSize(14);
        editor.setShowPrintMargin(false);
        editor.setOptions({
            enableBasicAutocompletion: true,
            enableSnippets: true,
            showLineNumbers: true,
            tabSize: 4,
        });

        editor.setValue(shapeData.script || "", -1);
        editor.clearSelection();

        document.getElementById("run-btn").addEventListener("click", handleRun);
        document.getElementById("refresh-data-btn").addEventListener("click", handleRefreshData);
    }

    async function handleRun() {
        var script = editor.getValue();
        var aceMode = mapLanguageToAceMode(currentLanguage);
        var mortyLang = mapLanguageToMortyLang(currentLanguage);

        setStatus("Running...", true);

        var dataToPass = currentData || {};
        var result = await executeScript(script, mortyLang, dataToPass);

        if (result.error) {
            setStatus("Error: " + result.error, false);
            document.getElementById("result-output").textContent =
                "Error: " + result.error;
        } else {
            setStatus("Done", true);
            var output = result.output !== undefined ? result.output : "(no output)";
            document.getElementById("result-output").textContent =
                typeof output === "string" ? output : JSON.stringify(output, null, 2);

            if (result.data) {
                currentData = result.data;
                renderDataPane(currentData);
            }
        }
    }

    async function handleRefreshData() {
        setStatus("Loading data...", true);
        var data = await fetchCaseData();
        if (data) {
            currentData = data;
            renderDataPane(data);
            setStatus("Data refreshed", true);
        }
    }

    function renderDataPane(data) {
        var el = document.getElementById("data-json");
        if (data === null || data === undefined) {
            el.innerHTML = '<span style="color:#888">(null)</span>';
        } else {
            el.innerHTML = syntaxHighlightJSON(data);
        }
    }

    /* ---- Boot ---- */

    (async function boot() {
        try {
            var shapeData = await fetchShapeData();

            initLanguageSelector(shapeData);
            initEditor(shapeData);

            var shapeNameEl = document.getElementById("top-shape");
            if (shapeData.shape_name) {
                shapeNameEl.textContent = shapeData.shape_name + " (" + shapeId + ")";
            }

            currentLanguage = shapeData.script_language || "python";
            var aceMode = mapLanguageToAceMode(currentLanguage);
            if (editor) {
                editor.session.setMode("ace/mode/" + aceMode);
            }

            await handleRefreshData();
            hideLoading();
        } catch (err) {
            setStatus(err.message, false);
            document.getElementById("result-output").textContent = err.message;
            document.getElementById("loading").classList.add("hidden");
        }
    })();
})();
