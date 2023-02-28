$(document).ready(function () {
    var button = document.createElement("Button");
    button.style = "bottom:15px;left:15px;position:fixed;z-index: 12;border-radius:100%;background-color:white; background: white url('https://www.bugheist.com/static/img/logo.png') no-repeat center; height: 50px; width: 50px; outline: none;background-size: 30px 30px;"
    document.body.appendChild(button);
    var url = window.location.href;
    var redirect_url = 'https://www.bugheist.com/report/?url=' + url;
    button.onclick = function () {
        var redirectWindow = window.open(redirect_url, '_blank');
        redirectWindow.location;
    }
});