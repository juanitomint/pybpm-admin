/*
 * Auth shim — intercepts Ext.Ajax and Ext.data.Connection requests to inject
 * the Bearer JWT from the bpm_session cookie before every outbound call.
 *
 * Handles two targets:
 *   1) pybpm-admin admin API endpoints (globals.module_url = '/admin/')
 *   2) pybpm-api editor persistence (globals.apiUrl prefix)
 *
 * On a 401 response the session cookie is cleared and the user is redirected
 * to /login so they can re-authenticate.
 */

(function () {
    'use strict';

    var COOKIE_NAME = 'bpm_session';
    var LOGIN_URL = '/login';

    function getCookie(name) {
        var match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
        return match ? match[2] : null;
    }

    /*
     * Patch Ext.Ajax.request to inject Authorization header before the request
     * is sent. Also intercept failure callbacks to detect 401 responses and
     * redirect the user back to login.
     */
    if (typeof Ext !== 'undefined' && Ext.Ajax) {

        var _origAjaxRequest = Ext.Ajax.request;

        Ext.Ajax.request = function (options) {
            options = options || {};
            options.headers = options.headers || {};

            // Inject Bearer token from session cookie for all requests.
            var token = getCookie(COOKIE_NAME);
            if (token) {
                options.headers['Authorization'] = 'Bearer ' + token;
            }

            var origSuccess = options.success;
            var origFailure = options.failure;

            options.success = function (response, opts) {
                if (typeof origSuccess === 'function') {
                    origSuccess(response, opts);
                }
            };

            options.failure = function (response, opts) {
                // If pybpm-admin returned 401, redirect the user back to login.
                if (response && response.status === 401) {
                    // Clear the expired session cookie by setting max-age=0.
                    document.cookie = COOKIE_NAME + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
                    window.location.href = LOGIN_URL + '?redirect=' + encodeURIComponent(document.location.pathname + document.location.search + document.location.hash);
                }
                if (typeof origFailure === 'function') {
                    origFailure(response, opts);
                }
            };

            return _origAjaxRequest.call(Ext.Ajax, options);
        };

        // Also patch Ext.data.Connection for Store proxies.
        if (Ext.data.Connection) {
            var _origConnRequest = Ext.data.Connection.prototype.request;

            Ext.data.Connection.prototype.request = function (options) {
                options = options || {};
                options.headers = options.headers || {};

                var token = getCookie(COOKIE_NAME);
                if (token) {
                    options.headers['Authorization'] = 'Bearer ' + token;
                }

                var origSuccess = options.success;
                var origFailure = options.failure;

                options.success = function (response, opts) {
                    if (typeof origSuccess === 'function') {
                        origSuccess(response, opts);
                    }
                };

                options.failure = function (response, opts) {
                    if (response && response.status === 401) {
                        document.cookie = COOKIE_NAME + '=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/';
                        window.location.href = LOGIN_URL + '?redirect=' + encodeURIComponent(document.location.pathname + document.location.search + document.location.hash);
                    }
                    if (typeof origFailure === 'function') {
                        origFailure(response, opts);
                    }
                };

                return _origConnRequest.call(this, options);
            };
        }
    }

})();
