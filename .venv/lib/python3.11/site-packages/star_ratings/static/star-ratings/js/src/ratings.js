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
