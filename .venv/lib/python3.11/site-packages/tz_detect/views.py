from django.http import HttpResponse
from django.views.generic import View


class SetOffsetView(View):
    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        offset = request.POST.get("offset", None)
        if not offset:
            return HttpResponse("No 'offset' parameter provided", status=400)

        try:
            offset = int(offset)
        except ValueError:
            return HttpResponse("Invalid 'offset' value provided", status=400)

        request.session["detected_tz"] = int(offset)

        return HttpResponse("OK")
