import json
from base64 import b64decode
import importlib

from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.core.files.base import ContentFile
from django.shortcuts import redirect, get_object_or_404
from django.utils.crypto import get_random_string

from tellme.forms import FeedbackForm
from tellme.models import Feedback
from tellme import mail


def get_notification_function(path=None):
    path = path or getattr(settings, 'TELLME_NOTIFICATION_FUNCTION',
                           'tellme.mail.send_mail')
    module_path = '.'.join(path.split('.')[:-1])
    func_name = path.split('.')[-1]
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func


def post_feedback(request):
    if request.method == 'POST' and request.is_ajax():

        # Copy Post data names into names used into the model in order to automatically create the model/form
        # from the request dicts
        feedback = json.loads(request.POST["feedback"])
        if request.user.id:
            data = {'url': feedback['url'], 'browser': json.dumps(feedback['browser']), 'comment': feedback['note'],
                        'user': request.user.id}
        else:
            data = {'url': feedback['url'], 'browser': json.dumps(feedback['browser']), 'comment': feedback['note'],
                        'email': feedback.get('email')}
        imgstr = feedback['img'].split(';base64,')[1]
        file = {'screenshot': ContentFile(b64decode(imgstr), name="screenshot_" + get_random_string(6) + ".png")}
        form = FeedbackForm(data, file)
        # check whether it's valid:
        if form.is_valid():
            f = form.save()

            if hasattr(settings, 'TELLME_FEEDBACK_EMAIL'):
                send_notif = get_notification_function()
                send_notif(request, f)
            return JsonResponse({})
        else:
            return JsonResponse({'error': dict(form.errors)})

    else:
        return HttpResponseBadRequest()


def get_feedback_screenshot(request, pk):
    instance = get_object_or_404(Feedback, pk=pk)
    return redirect(instance.screenshot.url)
