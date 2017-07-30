$(document).ready(function () {
    var button = document.createElement("Button");
    button.style = "bottom:15px;left:15px;position:fixed;z-index: 12;border-radius:100%;background: url('https://www.bugheist.com/static/img/logo.0cc160e97934.png') no-repeat center; height: 50px; width: 50px; outline: none;background-size: 50px 50px;"
    document.body.appendChild(button);
    var url = window.location.href;
    var bugheist = 'https://www.bugheist.com/report/?url=' + url;
    button.onclick = function() {
        var redirectWindow = window.open(bugheist, '_blank');
        redirectWindow.location;
    }
});