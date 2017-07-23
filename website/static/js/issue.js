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
    new Clipboard('.btn');
    $('.copy-btn').on('click', function () {
        $.notify('Copied!', {style: "custom", className: "success"});
    });
});

    $(document).on('submit','#comments',function(e){
        e.preventDefault();
        $.ajax({
            type: 'POST',
            url: '/issue/comment/add/',
            data:{
                text_comment: $('#text_comment').val(),
                issue_pk: $('#issue_pk').val(),
                csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
            },
            success: function(data){
                 $('#target_div').html(data);
                 $('#text_comment').val('');
            }
        });
    });

    $('body').on('click', '.del_comment', function (e){
        e.preventDefault();
        if(confirm("Delete this comment?")==true){
            $.ajax({
                type: 'POST',
                url: "/issue/comment/delete/",
                data:{
                    comment_pk:$(this).attr('name'),
                    issue_pk: $('#issue_pk').val(),
                    csrfmiddlewaretoken: $('#comments input[name=csrfmiddlewaretoken]').val(),
                },
                success: function(data) {
                    $('#target_div').html(data);
                },
            });
        }
    });


    $('body').on('click', '.edit_comment', function (e){
        e.preventDefault();
        $('#edit_form_'+$(this).attr('name')).attr('style','');
        var comment_id = $(this).attr('name');
        var old_message = $('#text_div_'+comment_id).text();
        $('#text_comment_'+comment_id).val(old_message);
        $('#text_div_'+comment_id).text('');
    });

    $(document).on('submit','.edit_form',function(f){
        f.preventDefault();
        var comment_id = $(this).attr('name');
        var issue_pk = $('#text_div_'+comment_id).text();
        var old_message = $('#text_div_'+comment_id).text();

        $.ajax({
            type: 'GET',
            url: '/issue/'+ $('#issue_pk').val()+ '/comment/edit/',
            data:{
                comment_pk: comment_id,
                text_comment: $('#text_comment_'+comment_id).val() ,
                issue_pk: $('#issue_pk').val(),
            },
            success: function(data){
                 $('#target_div').html(data);
            }

        });
    });


    function ajax_complete() {
        var search = $('#text_comment').val();
        var data = { search: search };
        $.ajax({
            type: 'GET',
            url: '/comment/autocomplete/',
            data: data,
            dataType: 'jsonp',
            jsonp: 'callback',
            jsonpCallback: 'ajax_render',
        });
    }

    function ajax_render(data) {
        $('#text_comment').atwho({
            at: "@",
            data:data
        });
    }
