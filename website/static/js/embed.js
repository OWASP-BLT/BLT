$(document).ready(function () {
    // change this to be the server where blt is hosted
    var fqdn = "https://www.hosted-blt-server.com";
    var button = document.createElement("Button");
    button.style = "bottom:15px;left:15px;position:fixed;z-index: 12;border-radius:100%;background-color:white; background: url('https://api.screenshotlayer.com/api/capture?access_key=<YOUR_ACCESS_KEY>&url=" + encodeURIComponent(window.location.href) + "') no-repeat center; height: 50px; width: 50px; outline: none;background-size: 30px 30px;"
    document.body.appendChild(button);
    var url = window.location.href;
    var redirect_url = fqdn + url;
    button.onclick = function () {
        var redirectWindow = window.open(redirect_url, '_blank');
        redirectWindow.location;
    }
});

