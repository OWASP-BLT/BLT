(function(){

    areCookiesEnabled = function() {
        // Credit for this function goes to: http://stackoverflow.com/a/18114024/764723
        var cookieEnabled = navigator.cookieEnabled;
        var cookieEnabledSupported;

        // When cookieEnabled flag is present and false then cookies are disabled.
        if (cookieEnabled === false) {
            return false;
        }

        // If cookieEnabled is null or undefined then assume the browser 
        // doesn't support this flag
        if (cookieEnabled !== false && !cookieEnabled) {
            cookieEnabledSupported = false;
        } else {
            cookieEnabledSupported = true;
        }


        // try to set a test cookie if we can't see any cookies and we're using 
        // either a browser that doesn't support navigator.cookieEnabled
        // or IE (which always returns true for navigator.cookieEnabled)
        if (!document.cookie && (!cookieEnabledSupported || /*@cc_on!@*/false)) {
            document.cookie = "testcookie=1";

            if (!document.cookie) {
                return false;
            } else {
                document.cookie = "testcookie=; expires=" + new Date(0).toUTCString();
            }
        }

        return true;
    };

    var createXMLHttp = function() {
        var xmlHttp = null;
        // Use XMLHttpRequest where available
        if (typeof(XMLHttpRequest) !== undefined) {
            xmlHttp = new XMLHttpRequest();
            return xmlHttp;
        // IE
        } else if (window.ActiveXObject) {
            var ieXMLHttpVersions = ['MSXML2.XMLHttp.5.0', 'MSXML2.XMLHttp.4.0', 'MSXML2.XMLHttp.3.0', 'MSXML2.XMLHttp', 'Microsoft.XMLHttp'];
            for (var i = 0; i < ieXMLHttpVersions.length; i++) {
                    try {
                        xmlHttp = new ActiveXObject(ieXMLHttpVersions[i]);
                        return xmlHttp;
                    } catch (e) {}
            }
        }
    };

    if(!areCookiesEnabled()) {
        // If cookies are disabled then storing the timezone in the user's 
        // session is a hopeless task and will trigger a request for each 
        // page load. Therefore, we shouldn't bother.
        return;
    }

    var xmlHttp = createXMLHttp();
    if(xmlHttp) {
        xmlHttp.open('post', window.tz_set_endpoint, true);
        xmlHttp.setRequestHeader('Content-type', 'application/x-www-form-urlencoded');
        xmlHttp.setRequestHeader(window.csrf_header_name, window.csrf_token);
        xmlHttp.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
        xmlHttp.send("offset=" + (new Date()).getTimezoneOffset());
    }

}());