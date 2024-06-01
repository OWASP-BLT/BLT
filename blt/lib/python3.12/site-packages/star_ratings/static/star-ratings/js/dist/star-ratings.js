(function(f){if(typeof exports==="object"&&typeof module!=="undefined"){module.exports=f()}else if(typeof define==="function"&&define.amd){define([],f)}else{var g;if(typeof window!=="undefined"){g=window}else if(typeof global!=="undefined"){g=global}else if(typeof self!=="undefined"){g=self}else{g=this}g.starRatings = f()}})(function(){var define,module,exports;return (function e(t,n,r){function s(o,u){if(!n[o]){if(!t[o]){var a=typeof require=="function"&&require;if(!u&&a)return a(o,!0);if(i)return i(o,!0);var f=new Error("Cannot find module '"+o+"'");throw f.code="MODULE_NOT_FOUND",f}var l=n[o]={exports:{}};t[o][0].call(l.exports,function(e){var n=t[o][1][e];return s(n?n:e)},l,l.exports,e,t,n,r)}return n[o].exports}var i=typeof require=="function"&&require;for(var o=0;o<r.length;o++)s(r[o]);return s})({1:[function(require,module,exports){
module.exports = require('./src/ratings');

},{"./src/ratings":2}],2:[function(require,module,exports){
var rest = require('./rest.js');
var utils = require('./utils');

/*********************
 * Initialise ratings
 *********************/
function init () {
    var ratingActions = document.querySelectorAll(".star-ratings-rate-action"),
        i;

    // Add click events to stars
    for (i = 0; i < ratingActions.length; i += 1) {
        bindRatings(ratingActions[i]);
    }
}


/*********************
 * Bind ratings
 *********************/
function bindRatings(el) {
    el.addEventListener("submit", ratingSubmit);

    el.onmouseenter = function () {
        var maxRating = getMaxRating(this);
        var scoreEl = this.querySelector('[name=score]');

        if (scoreEl){
            var parent = utils.findParent(this, "star-ratings");
            parent.querySelector(".star-ratings-rating-foreground").style.width = 100 / maxRating * scoreEl.value + "%";
        }
    };

    el.onmouseleave = function () {
        var avgRating = getAvgRating(this);
        var maxRating = getMaxRating(this);
        var parent = utils.findParent(this, "star-ratings");
        var percentage = 100 / maxRating * avgRating + "%";
        parent.querySelector(".star-ratings-rating-foreground").style.width = percentage;
    };
}


/*********************
 * Rating click event
 *********************/
function ratingSubmit(ev) {
    ev.stopPropagation();
    ev.preventDefault();

    var form = ev.target;

    var data = [].reduce.call(form.elements, function(data, element) {
        data[element.name] = element.value;
        return data;
    }, {});

    rate(form.action, data, this);
}


/*********************
 * Rate instance
 *********************/
function rate(url, data, sender) {
    rest.post(url, data, function (rating) {
        updateRating(rating, sender);
        dispatchRateSuccessEvent(rating, sender);
    }, function (errors) {
        showError(errors, sender);
        dispatchRateFailEvent(errors, sender);
    });
}


function _getEvent(name, detail) {
    if (typeof CustomEvent === 'undefined') {
        var evt = document.createEvent('CustomEvent');
        evt.initCustomEvent(name, true, true, detail);
        return evt;
    }
    else {
        return new CustomEvent(name, {
            detail: detail,
            bubbles: true,
            cancelable: true
        });
    }
}


function dispatchRateSuccessEvent(rating, sender) {
    sender.dispatchEvent(_getEvent(
        'rate-success',
        {
            sender: sender,
            rating: rating
        }
    ))
}


function dispatchRateFailEvent(error, sender) {
    sender.dispatchEvent(_getEvent(
        'rate-failed',
        {
            sender: sender,
            error: error
        }
    ))
}


function getMaxRating(el) {
    var parent = utils.findParent(el, "star-ratings");
    if (parent) {
        return parseInt(parent.getAttribute('data-max-rating'));
    }

    return -1;
}


function getAvgRating(el) {
    var parent = utils.findParent(el, "star-ratings");
    if (parent) {
        return parseFloat(parent.getAttribute('data-avg-rating'));
    }

    return -1;
}


/*********************
 * Update rating
 *********************/
function updateRating(rating, sender) {
    var parent = utils.findParent(sender, "star-ratings"),
        valueElem;

    if (parent === undefined || parent === null) {
        return;
    }

    parent.setAttribute("data-avg-rating", rating.average);
    var avgElem = parent.getElementsByClassName("star-ratings-rating-average")[0];
    if(avgElem) {
        valueElem = avgElem.getElementsByClassName('star-ratings-rating-value')[0];
        if (valueElem ) {
            var average = rating.average.toFixed(2);

            // suppress . if 0.
            if (rating.average === 0){
                average = 0
            }

            valueElem.innerHTML = average
        }
    }

    var countElem = parent.getElementsByClassName("star-ratings-rating-count")[0];
    if(countElem) {
        valueElem = countElem.getElementsByClassName('star-ratings-rating-value')[0];
        if (valueElem) {
            valueElem.innerHTML = rating.count;
        }
    }

    var userElem = parent.getElementsByClassName("star-ratings-rating-user")[0];
    var clearElem = parent.getElementsByClassName('star-ratings-clear')[0];
    if(userElem) {
        valueElem = userElem.getElementsByClassName('star-ratings-rating-value')[0];
        if (valueElem) {
            if (rating.user_rating == null && valueElem.getAttribute('data-when-null', false)){
                rating.user_rating = valueElem.getAttribute('data-when-null');

                if (clearElem) {
                    clearElem.classList.remove('star-ratings-clear-visible');
                    clearElem.classList.add('star-ratings-clear-hidden');
                }
            }
            else {
                if (clearElem) {
                    clearElem.classList.remove('star-ratings-clear-hidden');
                    clearElem.classList.add('star-ratings-clear-visible');
                }
            }
            valueElem.innerHTML = rating.user_rating;
        }
    }

    parent.querySelector(".star-ratings-rating-foreground").style.width = rating.percentage + '%';
}

function toggleClass (el, cls) {
    if (el.classList.contains(cls)) {
        el.classList.remove(cls);
    } else {
        el.classList.add(cls);
    }
}

function showError (errors, sender) {
    var parent = utils.findParent(sender, "star-ratings");
    if (parent === undefined || parent === null) {
        return;
    }
    parent.querySelector(".star-ratings-errors").innerHTML = errors.error;
    setTimeout(function () {
        parent.querySelector(".star-ratings-errors").innerHTML = "";
    }, 2500);
}

/*********************
 * Only initialise ratings
 * if there is something to rate
 *********************/
document.addEventListener('DOMContentLoaded', function(event) {
    if (document.querySelector('.star-ratings')) {
        init();
    }
});


module.exports = {
    bindRating: bindRatings
};

},{"./rest.js":3,"./utils":4}],3:[function(require,module,exports){
/*jslint browser:true */
"use strict";


var djangoRemarkRest = {
    getCookie: function (name) {
        // From https://docs.djangoproject.com/en/1.7/ref/contrib/csrf/
        var cookieValue = null, cookies, i, cookie;
        if (document.cookie && document.cookie !== '') {
            cookies = document.cookie.split(';');
            for (i = 0; i < cookies.length; i += 1) {
                cookie = cookies[i].trim(); // Doesn't work in all browsers
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },

    setCSRFToken: function (req) {
        var token = this.getCookie('csrftoken');

        // attempt to get token from DOM if it's not accessible from the cookie.
        // https://docs.djangoproject.com/en/dev/ref/csrf/#acquiring-csrf-token-from-html
        if (token == null){
            token = document.querySelector('[name=csrfmiddlewaretoken]').value;
        }

        req.setRequestHeader("X-CSRFToken", token);
        return req
    },

    makeRequest: function (url, method, success, fail) {
        var req = new XMLHttpRequest();
        if (req.overrideMimeType !== undefined) {
            req.overrideMimeType("application/json");
        }
        req.open(method, url, true);
        req.setRequestHeader('Content-Type', 'application/json');
        req.setRequestHeader('X-Requested-With', 'XMLHttpRequest');

        // When done processing data
        req.onreadystatechange = function () {
            if (req.readyState !== 4) {
                return;
            }

            if (req.status >= 200 && req.status <= 299) {
                if (success) {
                    if (req.responseText) {
                        success(JSON.parse(req.responseText));
                    } else { success(); }
                }
            } else {
                if (fail) {
                    fail(JSON.parse(req.responseText));
                }
            }
        };

        return req;
    },

    get: function (url, data, success, fail) {
        var req = this.makeRequest(url, 'GET', success, fail);
        req.send(JSON.stringify(data));
    },

    post: function (url, data, success, fail) {
        var req = this.makeRequest(url, 'POST', success, fail);
        req = this.setCSRFToken(req)
        req.send(JSON.stringify(data));
    },

    put: function (url, data, success, fail) {
        var req = this.makeRequest(url, 'PUT', success, fail);
        req = this.setCSRFToken(req)
        req.send(JSON.stringify(data));
    },

    patch: function (url, data, success, fail) {
        var req = this.makeRequest(url, 'PATCH', success, fail);
        req = this.setCSRFToken(req)
        req.send(JSON.stringify(data));
    },

    "delete": function (url, data, success, fail) {
        var req = this.makeRequest(url, 'DELETE', success, fail);
        req = this.setCSRFToken(req)
        req.send(JSON.stringify(data));
    }
};


module.exports = djangoRemarkRest;

},{}],4:[function(require,module,exports){
/**************************
 * Check if an element has a class
 **************************/
function hasClass (el, name) {
    return (' ' + el.className + ' ').indexOf(' ' + name + ' ') > -1;
}


/**************************
 * Find parent element
 **************************/
function findParent(el, className) {
    var parentNode = el.parentNode;
    while (hasClass(parentNode, className) === false) {
        if (parentNode.parentNode === undefined) {
            return null;
        }
        parentNode = parentNode.parentNode;
    }
    return parentNode
}


module.exports = {
    hasClass: hasClass,
    findParent: findParent
};

},{}]},{},[1])(1)
});
