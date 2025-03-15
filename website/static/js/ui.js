$(document).ready(function () {

    var prev_html = $('.user-menu .dropdown-toggle').html();
    var small_icon = false;

    $(window).resize(function () {
        if ($(window).width() < 400 && !small_icon) {
            small_icon = true;
            $('.user-menu .dropdown-toggle').html("<label>&#9776</label>");
            return;
        }
        if ($(window).width() > 400 && small_icon) {
            small_icon = false;
            $('.user-menu .dropdown-toggle').html(prev_html);
            return;
        }
    });

    $('.edit-pic').click(function () {
        $('.update-pic').show();
        $('.edit-pic').hide();
    });

    $("#startTour").click(function () {
        introJs().start();
    });

    $.notify.addStyle('custom', {
        html: "<div><span data-notify-text/></div>",
        classes: {
            base: {
                "border-radius": "5px",
                "background-color": "grey",
                "color": "white",
                "padding": "10px 40px",
                "font-size": "20px"
            },
            success: {
                "color": "#4efe00"
            },
            danger: {
                "color": "#f00"
            }
        }
    });

    $('[data-toggle="popover"]').popover({
        trigger: "hover",
        html: true,
        content: function () {
            var user = $(this).text();
            var tag = $(this).data('tag');
            var img = $(this).parent().parent().parent().find('img:first').attr('src');
            return '<div class="row">'
                + '<div class="col-md-3"><img src="' + img + '" height="50"></div>'
                + '<div class="col-md-7 col-md-offset-2">'
                + '<strong>' + user + '</strong>'
                + '<p><div class="label label-default">' + tag + '</div></p>'
                + '</div>'
                + '</div>';
        }
    });
});

