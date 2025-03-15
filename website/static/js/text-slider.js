$(document).ready(function () {
    var lines = $('.hero .text-slider-line');
    var n = lines.length;
    var i = 0;
    $(lines[0]).fadeIn();
    var changeText = setInterval(function () {

        $(lines[i]).fadeOut();
        if (i == (n - 1)) {
            i = 0;
        }
        else {
            i++;
        }
        setTimeout(function () {
            $(lines[i]).fadeIn();
        }, 500);
    }, 2000);


});

