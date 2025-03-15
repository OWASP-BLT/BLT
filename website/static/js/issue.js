function renderer(data) {
    $('#text_comment').atwho({
        at: "@",
        data: data
    });
}

window.twttr = (function (d, s, id) {

    var js, fjs = d.getElementsByTagName(s)[0], t = window.twttr || {};
    if (d.getElementById(id)) return t;
    js = d.createElement(s);
    js.id = id;
    js.src = "https://platform.twitter.com/widgets.js";
    fjs.parentNode.insertBefore(js, fjs);
    t._e = [];

    t.ready = function (f) {
        t._e.push(f);
    };
    return t;

}(document, "script", "twitter-wjs"));

(function (d, s, id) {
    var js, fjs = d.getElementsByTagName(s)[0];
    if (d.getElementById(id)) return;
    js = d.createElement(s);
    js.id = id;
    js.src = "//connect.facebook.net/en_US/sdk.js#xfbml=1&version=v2.7&appId=236647900066394";
    fjs.parentNode.insertBefore(js, fjs);
}(document, 'script', 'facebook-jssdk'));

$(function () {
    var comment_id, old_message;

    new Clipboard('.btn');
    $('.copy-btn').on('click', function () {
        $.notify('Copied!', {style: "custom", className: "success"});
    });

    $(document).on('submit', '#comments', function (e) {
        e.preventDefault();
        if ($('#text_comment').val().trim().length == 0) {
            $('.alert-danger').removeClass("hidden");
            return;
        }
        $('.alert-danger').addClass("hidden");
        $.ajax({
            type: 'POST',
            url: '/issue/comment/add/',
            data: {
                text_comment: $('#text_comment').val().trim(),
                issue_pk: $('#issue_pk').val(),
                csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
            },
            success: function (data) {
                $('#target_div').html(data);
                $('#text_comment').val('');
            }
        });
    });

    $('body').on('click', '.del_comment', function (e) {
        e.preventDefault();
        if (confirm("Delete this comment?") == true) {
            $.ajax({
                type: 'POST',
                url: "/issue/comment/delete/",
                data: {
                    comment_pk: $(this).attr('name'),
                    issue_pk: $('#issue_pk').val(),
                    csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
                },
                success: function (data) {
                    $('#target_div').html(data);
                },
            });
        }
    });

    $('body').on('click', '.edit_comment', function (e) {
        e.preventDefault();
        old_message = $(this).parent().next().next().text();
        comment_id = $(this).attr('name');
        $(this).hide();
        $(this).next('.edit_comment').hide();
        $(this).next('.del_comment').hide();
        $(this).parent().next().find('textarea').val(old_message);
        $(this).parent().parent().next().show();
    });

    $(document).on('click', '.edit_form button[type="submit"]', function (e) {
        e.preventDefault();
        var issue_id = $('#issue_pk').val();
        var comment = $(this).prev().find('textarea').val();
        if (comment == '') return;
        $.ajax({
            type: 'GET',
            url: '/issue/' + issue_id + '/comment/edit/',
            data: {
                comment_pk: comment_id,
                text_comment: comment,
                issue_pk: issue_id,
            },
            success: function (data) {
                $('#target_div').html(data);
            }
        });
    });


    $('body').on('click', '.reply_comment', function (e) {
        e.preventDefault();
        comment_id = $(this).attr('name');
        $(this).parent().parent().parent().next().toggle();
    });

    $(document).on('click', '.reply_form button[type="submit"]', function (e) {
        e.preventDefault();
        var parent_id = $(this).val();
        var issue_id = $('#issue_pk').val();
        var comment = $(this).prev().find('textarea').val();
        if (comment == '') return;
        $.ajax({
            type: 'GET',
            url: '/issue/' + issue_id + '/comment/reply/',
            data: {
                comment_pk: comment_id,
                text_comment: comment,
                issue_pk: issue_id,
                parent_id: parent_id,
            },
            success: function (data) {
                $('#target_div').html(data);
            }
        });
    });

    $('body').on('input, keyup', 'textarea', function () {
        var search = $(this).val();
        var data = {search: search};
        $.ajax({
            type: 'GET',
            url: '/comment/autocomplete/',
            data: data,
            dataType: 'jsonp',
            jsonp: 'callback',
            jsonpCallback: 'renderer',
        });
    });


    $(document).on('click', '.cancel-comment-edit', function (e) {
        e.preventDefault();
        $('.edit_form').hide();
        $(this).parent().parent().find('.edit_comment').show();
        $(this).parent().parent().find('.del_comment').show();
        $(this).parent().parent().find('.text-comment').show();
    });

    $(document).on('click', '.cancel-comment-reply', function (e) {
        e.preventDefault();
        comment_id = $(this).attr('name');
        $(this).parent().parent().hide();
        $(this).parent().parent().prev().find('.edit_comment').show();
        $(this).parent().parent().prev().find('.del_comment').show();
        $(this).parent().parent().prev().find('.reply_comment').show();
    });
});

