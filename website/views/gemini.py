from django.shortcuts import render
from django.http import JsonResponse
from website.utils import call_gemini

def gemini_ui(request):
    return render(request, "gemini_input.html")  # <-- match your actual path

def test_gemini(request):
    prompt = request.GET.get("prompt")
    if not prompt:
        return JsonResponse({"error": "No prompt provided"}, status=400)
    try:
        response = call_gemini(prompt)
        return JsonResponse({"response": response})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
