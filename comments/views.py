import json
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import HttpResponse, render
from django.template.loader import render_to_string
from django.utils.html import escape

from website.models import Issue

from .models import Comment


@login_required(login_url="/accounts/login/")
def add_comment(request):
    pk = request.POST.get("issue_pk")
    issue = Issue.objects.get(pk=pk)
    if request.method == "POST":
        author = request.user.username
        author_url = os.path.join("/profile/", request.user.username)
        issue = issue
        text = request.POST.get("text_comment")
        text = escape(text)
        user_list = []
        temp_text = text.split()
        new_text = ""
        new_msg = ""
        for item in temp_text:
            msg = item
            if item[0] == "@":
                if User.objects.filter(username=item[1:]).exists():
                    user = User.objects.get(username=item[1:])
                    user_list.append(user)
                    msg = user.username
                    item = "<a href='/profile/{0}'>@{1}</a>".format(item[1:], item[1:])

            new_text = new_text + " " + item
            new_msg = new_msg + " " + msg

        for obj in user_list:
            msg_plain = render_to_string(
                "email/comment_mention.html",
                {
                    "name": obj.username,
                    "commentor": request.user,
                    "issue_pk": pk,
                    "comment": new_msg,
                },
            )
            msg_html = render_to_string(
                "email/comment_mention.html",
                {
                    "name": obj.username,
                    "commentor": request.user,
                    "issue_pk": pk,
                    "comment": new_msg,
                },
            )

            send_mail(
                "You have been mentioned in a comment",
                msg_plain,
                settings.EMAIL_TO_STRING[obj.email],
                html_message=msg_html,
            )

        comment = Comment(author=author, author_url=author_url, issue=issue, text=new_text)
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(
        request,
        "comments.html",
        {"all_comment": all_comment, "user": request.user},
    )


@login_required(login_url="/accounts/login")
def delete_comment(request):
    if request.method == "POST":
        issue = Issue.objects.get(pk=request.POST["issue_pk"])
        all_comment = Comment.objects.filter(issue=issue)
        comment = Comment.objects.get(pk=int(request.POST["comment_pk"]))
        try:
            show = comment.parent.pk
        except:
            show = -1
        if request.user.username != comment.author:
            return HttpResponse("Cannot delete this comment")
        comment.delete()
    return render(
        request,
        "comments.html",
        {
            "all_comment": all_comment,
            "user": request.user,
            "show": show,
        },
    )


@login_required(login_url="/accounts/login/")
def edit_comment(request, pk):
    if request.method == "GET":
        issue = Issue.objects.get(pk=request.GET["issue_pk"])
        comment = Comment.objects.get(pk=request.GET["comment_pk"])
        comment.text = request.GET.get("text_comment")
        comment.text = escape(comment.text)
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(
        request,
        "comments.html",
        {"all_comment": all_comment, "user": request.user},
    )


@login_required(login_url="/accounts/login/")
def reply_comment(request, pk):
    if request.method == "GET":
        parent_id = request.GET.get("parent_id")
        show = int(parent_id)
        parent_obj = Comment.objects.get(id=parent_id)
        author = request.user.username
        author_url = os.path.join("/profile/", request.user.username)
        issue = Issue.objects.get(pk=request.GET["issue_pk"])
        reply_text = request.GET.get("text_comment")
        reply_text = escape(reply_text)
        comment = Comment(author=author, author_url=author_url, issue=issue, text=reply_text, parent=parent_obj)
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(
        request,
        "comments.html",
        {"all_comment": all_comment, "user": request.user, "show": show},
    )


@login_required(login_url="/accounts/login")
def autocomplete(request):
    q_string = request.GET.get("search", "")
    q_string = escape(q_string)
    if len(q_string) == 0:
        return HttpResponse(request.GET["callback"] + "(" + json.dumps([]) + ");", content_type="application/json")
    q_list = q_string.split(" ")
    q_s = q_list[len(q_list) - 1]
    if len(q_s) == 0 or q_s[0] != "@":
        return HttpResponse(request.GET["callback"] + "(" + json.dumps([]) + ");", content_type="application/json")

    q_s = q_s[1:]
    search_qs = User.objects.filter(username__startswith=q_s)
    results = []
    for r in search_qs:
        results.append(r.username)
    resp = request.GET["callback"] + "(" + json.dumps(results) + ");"
    return HttpResponse(resp, content_type="application/json")

