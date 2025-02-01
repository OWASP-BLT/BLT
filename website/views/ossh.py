from django.shortcuts import render

from website.utils import fetch_github_user_data


def ossh_home(request):
    template = "ossh/home.html"
    return render(request, template)


def ossh_results(request):
    template = "ossh/results.html"

    if request.method == "POST":
        github_username = request.POST.get("github-username")
        user_data = fetch_github_user_data(github_username)
        print(user_data)
        context = {"username": github_username, "user_data": user_data}
        return render(request, template, context)
