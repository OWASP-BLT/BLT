$(document).ready(function () {
    $('.text-trunc').each(function (index, ele) {
        var text = $(ele).siblings('.small').text().trim()
        var actor = /^[^\s]+/.exec(text)
        var rest = text.slice(actor[0].length).trim().substring(0, 20).split(" ").slice(0, -1).join(" ") + "...";
        $(ele).text(actor[0] + ' ' + rest);
    })

    $('.more_info').click(function () {
        if ($(this)[0] == $('.open')[0]) {
            close_panel()
            return;
        }
        close_panel()
        $(this).html("<a>See less</a>")
        $(this).parent().animate({'height': '200px'})
        $(this).parent().parent().animate({'height': '200px'})
        $(this).parent().parent().parent().animate({'height': '200px'})
        $(this).siblings('.text-trunc').hide()
        $(this).siblings('.small').show()
        $(this).addClass('open')
    })

    function close_panel() {
        $('.open').html('<a>See more</a>')
        $('.open').parent().animate({'height': '160px'})
        $('.open').parent().parent().animate({'height': '160px'})
        $('.open').parent().parent().parent().animate({'height': '160px'})
        $('.open').siblings('.small').hide()
        $('.open').siblings('.text-trunc').show()
        $('.open').removeClass('open')
    }
})

