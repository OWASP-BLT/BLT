// feedback.js
// 2013, Kázmér Rapavi, https://github.com/ivoviz/feedback
// Licensed under the MIT license.
// Version 2.0

(function($){

    $.feedback = function(options) {

        var settings = $.extend({
            ajaxURL: 				'',
            headers:  {},
            postBrowserInfo: 		true,
            postHTML:				true,
            postURL:				true,
            proxy:					undefined,
            letterRendering:		false,
            initButtonText: 		'Send feedback',
            strokeStyle:			'black',
            shadowColor:			'black',
            shadowOffsetX:			1,
            shadowOffsetY:			1,
            shadowBlur:				10,
            lineJoin:				'bevel',
            lineWidth:				3,
            html2canvasURL:			'html2canvas.js',
            feedbackButton: 		'.feedback-btn',
            showDescriptionModal: 	true,
            isDraggable: 			true,
            onScreenshotTaken: 		function(){},
            tpl: {
                description:	'<div id="feedback-welcome"><div class="feedback-logo">Feedback</div><p>Feedback lets you send us suggestions about our products. We welcome problem reports, feature ideas and general comments.</p><p>Start by writing a brief description:</p><textarea id="feedback-note-tmp"></textarea><p>Next we\'ll let you identify areas of the page related to your description.</p><button id="feedback-welcome-next" class="feedback-next-btn feedback-btn-gray">Next</button><div id="feedback-welcome-error">Please enter a description.</div><div class="feedback-wizard-close"></div></div>',
                highlighter:	'<div id="feedback-highlighter"><div class="feedback-logo">Feedback</div><p>Click and drag on the page to help us better understand your feedback. You can move this dialog if it\'s in the way.</p><button class="feedback-sethighlight feedback-active"><div class="ico"></div><span>Highlight</span></button><label>Highlight areas relevant to your feedback.</label><button class="feedback-setblackout"><div class="ico"></div><span>Black out</span></button><label class="lower">Black out any personal information.</label><div class="feedback-buttons"><button id="feedback-highlighter-next" class="feedback-next-btn feedback-btn-gray">Next</button><button id="feedback-highlighter-back" class="feedback-back-btn feedback-btn-gray">Back</button></div><div class="feedback-wizard-close"></div></div>',
                overview:		'<div id="feedback-overview"><div class="feedback-logo">Feedback</div><div id="feedback-overview-description"><div id="feedback-overview-description-text"><h3>Description</h3><h3 class="feedback-additional">Additional info</h3><div id="feedback-additional-none"><span>None</span></div><div id="feedback-browser-info"><span>Browser Info</span></div><div id="feedback-page-info"><span>Page Info</span></div><div id="feedback-page-structure"><span>Page Structure</span></div></div></div><div id="feedback-overview-screenshot"><h3>Screenshot</h3></div><div class="feedback-buttons"><button id="feedback-submit" class="feedback-submit-btn feedback-btn-blue">Submit</button><button id="feedback-overview-back" class="feedback-back-btn feedback-btn-gray">Back</button></div><div id="feedback-overview-error">Please enter a description.</div><div class="feedback-wizard-close"></div></div>',
                submitLoading:  '<div id="feedback-submit-loading"><div class="feedback-logo">Feedback</div><p>Loading...</p></div>',
                submitSuccess:	'<div id="feedback-submit-success"><div class="feedback-logo">Feedback</div><p>Thank you for your feedback. We value every piece of feedback we receive.</p><p>We cannot respond individually to every one, but we will use your comments as we strive to improve your experience.</p><button class="feedback-close-btn feedback-btn-blue">OK</button><div class="feedback-wizard-close"></div></div>',
                submitError:	'<div id="feedback-submit-error"><div class="feedback-logo">Feedback</div><p>Sadly an error occured while sending your feedback. Please try again.</p><button class="feedback-close-btn feedback-btn-blue">OK</button><div class="feedback-wizard-close"></div></div>'
            },
            onClose: 				function() {},
            screenshotStroke:		true,
            highlightElement:		true,
            initialBox:				false
        }, options);
        var supportedBrowser = !!window.HTMLCanvasElement;
        var isFeedbackButtonNative = settings.feedbackButton == '.feedback-btn';
        var _html2canvas = false;
        if (supportedBrowser) {
            if(isFeedbackButtonNative) {
                $('body').append('<button class="feedback-btn feedback-btn-gray feedback-btn-native">' + settings.initButtonText + '</button>');
            }
            $(document).on('click.feedback', settings.feedbackButton, function(){
                if(isFeedbackButtonNative) {
                    $(this).hide();
                }
                if (!_html2canvas) {
                    $.getScript(settings.html2canvasURL, function() {
                        _html2canvas = true;
                    });
                }
                var canDraw = false,
                    img = '',
                    h 	= $(document).height(),
                    w 	= $(document).width(),
                    tpl = '<div id="feedback-module">';

                if (settings.initialBox) {
                    tpl += settings.tpl.description;
                }

                tpl += settings.tpl.highlighter + settings.tpl.overview + '<canvas id="feedback-canvas"></canvas><div id="feedback-helpers"></div><input id="feedback-note" name="feedback-note" type="hidden"></div>';

                $('body').append(tpl);

                moduleStyle = {
                    'position':	'absolute',
                    'left': 	'0px',
                    'top':		'0px'
                };
                canvasAttr = {
                    'width': w,
                    'height': h
                };

                $('#feedback-module').css(moduleStyle);
                $('#feedback-canvas').attr(canvasAttr).css('z-index', '30000');

                if (!settings.initialBox) {
                    $('#feedback-highlighter-back').remove();
                    canDraw = true;
                    $('#feedback-canvas').css('cursor', 'crosshair');
                    $('#feedback-helpers').show();
                    $('#feedback-welcome').hide();
                    $('#feedback-highlighter').show();
                }

                if(settings.isDraggable) {
                    $('#feedback-highlighter').on('mousedown.feedback', function(e) {
                        var $d = $(this).addClass('feedback-draggable'),
                            drag_h 	= $d.outerHeight(),
                            drag_w 	= $d.outerWidth(),
                            pos_y 	= $d.offset().top + drag_h - e.pageY,
                            pos_x 	= $d.offset().left + drag_w - e.pageX;
                        $d.css('z-index', 40000).parents().on('mousemove.feedback', function(e) {
                            _top 	= e.pageY + pos_y - drag_h;
                            _left 	= e.pageX + pos_x - drag_w;
                            _bottom = drag_h - e.pageY;
                            _right 	= drag_w - e.pageX;

                            if (_left < 0) _left = 0;
                            if (_top < 0) _top = 0;
                            if (_right > $(window).width())
                                _left = $(window).width() - drag_w;
                            if (_left > $(window).width() - drag_w)
                                _left = $(window).width() - drag_w;
                            if (_bottom > $(document).height())
                                _top = $(document).height() - drag_h;
                            if (_top > $(document).height() - drag_h)
                                _top = $(document).height() - drag_h;

                            $('.feedback-draggable').offset({
                                top:	_top,
                                left:	_left
                            }).on("mouseup", function() {
                                $(this).removeClass('feedback-draggable');
                            });
                        });
                        e.preventDefault();
                    }).on('mouseup.feedback', function(){
                        $(this).removeClass('feedback-draggable');
                        $(this).parents().off('mousemove mousedown');
                    });
                }

                var ctx = $('#feedback-canvas')[0].getContext('2d');

                ctx.fillStyle = 'rgba(102,102,102,0.5)';
                ctx.fillRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());

                rect 		= {};
                drag 		= false;
                highlight 	= 1,
                    post		= {};

                if (settings.postBrowserInfo) {
                    post.browser 				= {};
                    post.browser.appCodeName	= navigator.appCodeName;
                    post.browser.appName		= navigator.appName;
                    post.browser.appVersion		= navigator.appVersion;
                    post.browser.cookieEnabled	= navigator.cookieEnabled;
                    post.browser.onLine			= navigator.onLine;
                    post.browser.platform		= navigator.platform;
                    post.browser.userAgent		= navigator.userAgent;
                    post.browser.plugins		= [];

                    $.each(navigator.plugins, function(i) {
                        post.browser.plugins.push(navigator.plugins[i].name);
                    });
                    $('#feedback-browser-info').show();
                }

                if (settings.postURL) {
                    post.url = document.URL;
                    $('#feedback-page-info').show();
                }

                if (settings.postHTML) {
                    post.html = $('html').html();
                    $('#feedback-page-structure').show();
                }

                if (!settings.postBrowserInfo && !settings.postURL && !settings.postHTML)
                    $('#feedback-additional-none').show();

                $(document).on('mousedown.feedback', '#feedback-canvas', function(e) {
                    if (canDraw) {

                        rect.startX = e.pageX - $(this).offset().left;
                        rect.startY = e.pageY - $(this).offset().top;
                        rect.w = 0;
                        rect.h = 0;
                        drag = true;
                    }
                });

                $(document).on('mouseup.feedback', function(){
                    if (canDraw) {
                        drag = false;

                        var dtop	= rect.startY,
                            dleft	= rect.startX,
                            dwidth	= rect.w,
                            dheight	= rect.h;
                        dtype	= 'highlight';

                        if (dwidth == 0 || dheight == 0) return;

                        if (dwidth < 0) {
                            dleft 	+= dwidth;
                            dwidth 	*= -1;
                        }
                        if (dheight < 0) {
                            dtop 	+= dheight;
                            dheight *= -1;
                        }

                        if (dtop + dheight > $(document).height())
                            dheight = $(document).height() - dtop;
                        if (dleft + dwidth > $(document).width())
                            dwidth = $(document).width() - dleft;

                        if (highlight == 0)
                            dtype = 'blackout';

                        $('#feedback-helpers').append('<div class="feedback-helper" data-type="' + dtype + '" data-time="' + Date.now() + '" style="position:absolute;top:' + dtop + 'px;left:' + dleft + 'px;width:' + dwidth + 'px;height:' + dheight + 'px;z-index:30000;"></div>');

                        redraw(ctx);
                        rect.w = 0;
                    }

                });

                $(document).on('mousemove.feedback', function(e) {
                    if (canDraw && drag) {
                        $('#feedback-highlighter').css('cursor', 'default');

                        rect.w = (e.pageX - $('#feedback-canvas').offset().left) - rect.startX;
                        rect.h = (e.pageY - $('#feedback-canvas').offset().top) - rect.startY;

                        ctx.clearRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
                        ctx.fillStyle = 'rgba(102,102,102,0.5)';
                        ctx.fillRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
                        $('.feedback-helper').each(function() {
                            if ($(this).attr('data-type') == 'highlight')
                                drawlines(ctx, parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                        });
                        if (highlight==1) {
                            drawlines(ctx, rect.startX, rect.startY, rect.w, rect.h);
                            ctx.clearRect(rect.startX, rect.startY, rect.w, rect.h);
                        }
                        $('.feedback-helper').each(function() {
                            if ($(this).attr('data-type') == 'highlight')
                                ctx.clearRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                        });
                        $('.feedback-helper').each(function() {
                            if ($(this).attr('data-type') == 'blackout') {
                                ctx.fillStyle = 'rgba(0,0,0,1)';
                                ctx.fillRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height())
                            }
                        });
                        if (highlight == 0) {
                            ctx.fillStyle = 'rgba(0,0,0,0.5)';
                            ctx.fillRect(rect.startX, rect.startY, rect.w, rect.h);
                        }
                    }
                });

                if (settings.highlightElement) {
                    var highlighted = [],
                        tmpHighlighted = [],
                        hidx = 0;

                    $(document).on('mousemove.feedback click.feedback', '#feedback-canvas',function(e) {
                        if (canDraw) {
                            redraw(ctx);
                            tmpHighlighted = [];

                            $('#feedback-canvas').css('cursor', 'crosshair');

                            $('* :not(body,script,iframe,div,section,.feedback-btn,#feedback-module *)').each(function(){
                                if ($(this).attr('data-highlighted') === 'true')
                                    return;

                                if (e.pageX > $(this).offset().left && e.pageX < $(this).offset().left + $(this).width() && e.pageY > $(this).offset().top + parseInt($(this).css('padding-top'), 10) && e.pageY < $(this).offset().top + $(this).height() + parseInt($(this).css('padding-top'), 10)) {
                                    tmpHighlighted.push($(this));
                                }
                            });

                            var $toHighlight = tmpHighlighted[tmpHighlighted.length - 1];

                            if ($toHighlight && !drag) {
                                $('#feedback-canvas').css('cursor', 'pointer');

                                var _x = $toHighlight.offset().left - 2,
                                    _y = $toHighlight.offset().top - 2,
                                    _w = $toHighlight.width() + parseInt($toHighlight.css('padding-left'), 10) + parseInt($toHighlight.css('padding-right'), 10) + 6,
                                    _h = $toHighlight.height() + parseInt($toHighlight.css('padding-top'), 10) + parseInt($toHighlight.css('padding-bottom'), 10) + 6;

                                if (highlight == 1) {
                                    drawlines(ctx, _x, _y, _w, _h);
                                    ctx.clearRect(_x, _y, _w, _h);
                                    dtype = 'highlight';
                                }

                                $('.feedback-helper').each(function() {
                                    if ($(this).attr('data-type') == 'highlight')
                                        ctx.clearRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                                });

                                if (highlight == 0) {
                                    dtype = 'blackout';
                                    ctx.fillStyle = 'rgba(0,0,0,0.5)';
                                    ctx.fillRect(_x, _y, _w, _h);
                                }

                                $('.feedback-helper').each(function() {
                                    if ($(this).attr('data-type') == 'blackout') {
                                        ctx.fillStyle = 'rgba(0,0,0,1)';
                                        ctx.fillRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                                    }
                                });

                                if (e.type == 'click' && e.pageX == rect.startX && e.pageY == rect.startY) {
                                    $('#feedback-helpers').append('<div class="feedback-helper" data-highlight-id="' + hidx + '" data-type="' + dtype + '" data-time="' + Date.now() + '" style="position:absolute;top:' + _y + 'px;left:' + _x + 'px;width:' + _w + 'px;height:' + _h + 'px;z-index:30000;"></div>');
                                    highlighted.push(hidx);
                                    ++hidx;
                                    redraw(ctx);
                                }
                            }
                        }
                    });
                }

                $(document).on('mouseleave.feedback', 'body,#feedback-canvas', function() {
                    redraw(ctx);
                });

                $(document).on('mouseenter.feedback', '.feedback-helper', function() {
                    redraw(ctx);
                });

                $(document).on('click.feedback', '#feedback-welcome-next', function() {
                    if ($('#feedback-note').val().length > 0) {
                        canDraw = true;
                        $('#feedback-canvas').css('cursor', 'crosshair');
                        $('#feedback-helpers').show();
                        $('#feedback-welcome').hide();
                        $('#feedback-highlighter').show();
                    }
                    else {
                        $('#feedback-welcome-error').show();
                    }
                });

                $(document).on('mouseenter.feedback mouseleave.feedback', '.feedback-helper', function(e) {
                    if (drag)
                        return;

                    rect.w = 0;
                    rect.h = 0;

                    if (e.type === 'mouseenter') {
                        $(this).css('z-index', '30001');
                        $(this).append('<div class="feedback-helper-inner" style="width:' + ($(this).width() - 2) + 'px;height:' + ($(this).height() - 2) + 'px;position:absolute;margin:1px;"></div>');
                        $(this).append('<div id="feedback-close"></div>');
                        $(this).find('#feedback-close').css({
                            'top' 	: -1 * ($(this).find('#feedback-close').height() / 2) + 'px',
                            'left' 	: $(this).width() - ($(this).find('#feedback-close').width() / 2) + 'px'
                        });

                        if ($(this).attr('data-type') == 'blackout') {
                            /* redraw white */
                            ctx.clearRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
                            ctx.fillStyle = 'rgba(102,102,102,0.5)';
                            ctx.fillRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
                            $('.feedback-helper').each(function() {
                                if ($(this).attr('data-type') == 'highlight')
                                    drawlines(ctx, parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                            });
                            $('.feedback-helper').each(function() {
                                if ($(this).attr('data-type') == 'highlight')
                                    ctx.clearRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                            });

                            ctx.clearRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height())
                            ctx.fillStyle = 'rgba(0,0,0,0.75)';
                            ctx.fillRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());

                            ignore = $(this).attr('data-time');

                            /* redraw black */
                            $('.feedback-helper').each(function() {
                                if ($(this).attr('data-time') == ignore)
                                    return true;
                                if ($(this).attr('data-type') == 'blackout') {
                                    ctx.fillStyle = 'rgba(0,0,0,1)';
                                    ctx.fillRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height())
                                }
                            });
                        }
                    }
                    else {
                        $(this).css('z-index','30000');
                        $(this).children().remove();
                        if ($(this).attr('data-type') == 'blackout') {
                            redraw(ctx);
                        }
                    }
                });

                $(document).on('click.feedback', '#feedback-close', function() {
                    if (settings.highlightElement && $(this).parent().attr('data-highlight-id'))
                        var _hidx = $(this).parent().attr('data-highlight-id');

                    $(this).parent().remove();

                    if (settings.highlightElement && _hidx)
                        $('[data-highlight-id="' + _hidx + '"]').removeAttr('data-highlighted').removeAttr('data-highlight-id');

                    redraw(ctx);
                });

                $('#feedback-module').on('click.feedback', '.feedback-wizard-close,.feedback-close-btn', function() {
                    close();
                });

                $(document).on('keyup.feedback', function(e) {
                    if (e.keyCode == 27)
                        close();
                });

                $(document).on('selectstart.feedback dragstart.feedback', function(e) {
                    e.preventDefault();
                });

                $(document).on('click.feedback', '#feedback-highlighter-back', function() {
                    canDraw = false;
                    $('#feedback-canvas').css('cursor', 'default');
                    $('#feedback-helpers').hide();
                    $('#feedback-highlighter').hide();
                    $('#feedback-welcome-error').hide();
                    $('#feedback-welcome').show();
                });

                $(document).on('mousedown.feedback', '.feedback-sethighlight', function() {
                    highlight = 1;
                    $(this).addClass('feedback-active');
                    $('.feedback-setblackout').removeClass('feedback-active');
                });

                $(document).on('mousedown.feedback', '.feedback-setblackout', function() {
                    highlight = 0;
                    $(this).addClass('feedback-active');
                    $('.feedback-sethighlight').removeClass('feedback-active');
                });

                $(document).on('click.feedback', '#feedback-highlighter-next', function() {
                    canDraw = false;
                    $('#feedback-canvas').css('cursor', 'default');
                    var sy = $(document).scrollTop(),
                        dh = $(window).height();
                    $('#feedback-helpers').hide();
                    $('#feedback-highlighter').hide();
                    if (!settings.screenshotStroke) {
                        redraw(ctx, false);
                    }
                    html2canvas($('body'), {
                        onrendered: function(canvas) {
                            if (!settings.screenshotStroke) {
                                redraw(ctx);
                            }
                            _canvas = $('<canvas id="feedback-canvas-tmp" width="'+ w +'" height="'+ dh +'"/>').hide().appendTo('body');
                            _ctx = _canvas.get(0).getContext('2d');
                            _ctx.drawImage(canvas, 0, sy, w, dh, 0, 0, w, dh);
                            img = _canvas.get(0).toDataURL();
                            $(document).scrollTop(sy);
                            post.img = img;
                            settings.onScreenshotTaken(post.img);
                            if(settings.showDescriptionModal) {
                                $('#feedback-canvas-tmp').remove();
                                $('#feedback-overview').show();
                                $('#feedback-overview-description-text>textarea').remove();
                                $('#feedback-overview-screenshot>img').remove();
                                $('<textarea id="feedback-overview-note">' + $('#feedback-note').val() + '</textarea>').insertAfter('#feedback-overview-description-text h3:eq(0)');
                                $('#feedback-overview-screenshot').append('<img class="feedback-screenshot" src="' + img + '" />');
                            }
                            else {
                                $('#feedback-module').remove();
                                close();
                                _canvas.remove();
                            }
                        },
                        proxy: settings.proxy,
                        letterRendering: settings.letterRendering
                    });
                });

                $(document).on('click.feedback', '#feedback-overview-back', function(e) {
                    canDraw = true;
                    $('#feedback-canvas').css('cursor', 'crosshair');
                    $('#feedback-overview').hide();
                    $('#feedback-helpers').show();
                    $('#feedback-highlighter').show();
                    $('#feedback-overview-error').hide();
                });

                $(document).on('keyup.feedback', '#feedback-note-tmp,#feedback-overview-note', function(e) {
                    var tx;
                    if (e.target.id === 'feedback-note-tmp')
                        tx = $('#feedback-note-tmp').val();
                    else {
                        tx = $('#feedback-overview-note').val();
                        $('#feedback-note-tmp').val(tx);
                    }

                    $('#feedback-note').val(tx);
                });

                $(document).on('click.feedback', '#feedback-submit', function() {
                    canDraw = false;

                    if ($('#feedback-note').val().length > 0) {
                        $('#feedback-submit-success,#feedback-submit-error').remove();
                        $('#feedback-overview').hide();
                        $("#feedback-module").append(settings.tpl.submitLoading);

                        post.img = img;
                        post.note = $('#feedback-note')?.val() || $("input[name=feedback-note]")?.val();
                        post.email = $("#feedback-user-email")?.val() || $("input[name=email]")?.val();
                        var data = {feedback: JSON.stringify(post)};
                        $.ajax({
                            url: settings.ajaxURL,
                            dataType: 'json',
                            type: 'POST',
                            data: data,
                            headers: settings.headers,
                            success: function() {
                                $('#feedback-module').append(settings.tpl.submitSuccess);
                            },
                            error: function(){
                                $('#feedback-module').append(settings.tpl.submitError);
                            }
                        });
                    }
                    else {
                        $('#feedback-overview-error').show();
                    }
                });
            });
        }

        function close() {
            canDraw = false;
            $(document).off('mouseenter.feedback mouseleave.feedback', '.feedback-helper');
            $(document).off('mouseup.feedback keyup.feedback');
            $(document).off('mousedown.feedback', '.feedback-setblackout');
            $(document).off('mousedown.feedback', '.feedback-sethighlight');
            $(document).off('mousedown.feedback click.feedback', '#feedback-close');
            $(document).off('mousedown.feedback', '#feedback-canvas');
            $(document).off('click.feedback', '#feedback-highlighter-next');
            $(document).off('click.feedback', '#feedback-highlighter-back');
            $(document).off('click.feedback', '#feedback-welcome-next');
            $(document).off('click.feedback', '#feedback-overview-back');
            $(document).off('mouseleave.feedback', 'body');
            $(document).off('mouseenter.feedback', '.feedback-helper');
            $(document).off('selectstart.feedback dragstart.feedback');
            $('#feedback-module').off('click.feedback', '.feedback-wizard-close,.feedback-close-btn');
            $(document).off('click.feedback', '#feedback-submit');

            if (settings.highlightElement) {
                $(document).off('click.feedback', '#feedback-canvas');
                $(document).off('mousemove.feedback', '#feedback-canvas');
            }
            $('[data-highlighted="true"]').removeAttr('data-highlight-id').removeAttr('data-highlighted');
            $('#feedback-module').remove();
            $('.feedback-btn').show();

            settings.onClose.call(this);
        }

        function redraw(ctx, border) {
            border = typeof border !== 'undefined' ? border : true;
            ctx.clearRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
            ctx.fillStyle = 'rgba(102,102,102,0.5)';
            ctx.fillRect(0, 0, $('#feedback-canvas').width(), $('#feedback-canvas').height());
            $('.feedback-helper').each(function() {
                if ($(this).attr('data-type') == 'highlight')
                    if (border)
                        drawlines(ctx, parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
            });
            $('.feedback-helper').each(function() {
                if ($(this).attr('data-type') == 'highlight')
                    ctx.clearRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
            });
            $('.feedback-helper').each(function() {
                if ($(this).attr('data-type') == 'blackout') {
                    ctx.fillStyle = 'rgba(0,0,0,1)';
                    ctx.fillRect(parseInt($(this).css('left'), 10), parseInt($(this).css('top'), 10), $(this).width(), $(this).height());
                }
            });
        }

        function drawlines(ctx, x, y, w, h) {
            ctx.strokeStyle		= settings.strokeStyle;
            ctx.shadowColor		= settings.shadowColor;
            ctx.shadowOffsetX	= settings.shadowOffsetX;
            ctx.shadowOffsetY	= settings.shadowOffsetY;
            ctx.shadowBlur		= settings.shadowBlur;
            ctx.lineJoin		= settings.lineJoin;
            ctx.lineWidth		= settings.lineWidth;

            ctx.strokeRect(x,y,w,h);

            ctx.shadowOffsetX	= 0;
            ctx.shadowOffsetY	= 0;
            ctx.shadowBlur		= 0;
            ctx.lineWidth		= 1;
        }

    };

}(jQuery));
