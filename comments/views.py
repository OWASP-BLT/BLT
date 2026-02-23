import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.shortcuts import HttpResponse, get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.html import escape

from website.models import Issue

from .models import Comment


def _get_issue_ct():
    """Return the ContentType for the Issue model."""
    return ContentType.objects.get_for_model(Issue)


@login_required(login_url="/accounts/login/")
def add_comment(request):
    if request.method == "POST":
        pk = request.POST.get("issue_pk")
        if not pk:
            return HttpResponse("Missing issue ID", status=400)
        try:
            pk = int(pk)
        except (ValueError, TypeError):
            return HttpResponse("Invalid issue ID", status=400)
        issue = get_object_or_404(Issue, pk=pk)
        author = request.user.username
        author_url = f"/profile/{request.user.username}"
        text = request.POST.get("text_comment")
        if not text:
            return HttpResponse("Missing comment text", status=400)
        text = escape(text)
        user_list = []
        temp_text = text.split()
        new_text = ""
        new_msg = ""
        for item in temp_text:
            msg = item
            if item and item[0] == "@":
                mentioned = User.objects.filter(username=item[1:]).first()
                if mentioned:
                    user_list.append(mentioned)
                    msg = f"@{mentioned.username}"
                    item = f"<a href='/profile/{item[1:]}'>@{item[1:]}</a>"

            new_text = new_text + " " + item
            new_msg = new_msg + " " + msg

        for obj in user_list:
            if not obj.email:
                continue
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
                settings.EMAIL_TO_STRING,
                [obj.email],
                html_message=msg_html,
            )

        issue_ct = _get_issue_ct()
        comment = Comment(
            author=author, author_url=author_url, content_type=issue_ct, object_id=issue.pk, text=new_text
        )
        comment.save()
        all_comment = Comment.objects.filter(content_type=issue_ct, object_id=issue.pk).select_related("parent")
        return render(
            request,
            "comments.html",
            {"all_comment": all_comment, "user": request.user},
        )
    return HttpResponse("Method not allowed", status=405)


@login_required(login_url="/accounts/login/")
def delete_comment(request):
    if request.method == "POST":
        issue_pk = request.POST.get("issue_pk")
        if not issue_pk:
            return HttpResponse("Missing issue ID", status=400)
        try:
            issue_pk = int(issue_pk)
        except (ValueError, TypeError):
            return HttpResponse("Invalid issue ID", status=400)
        issue = get_object_or_404(Issue, pk=issue_pk)
        comment_pk = request.POST.get("comment_pk")
        if not comment_pk:
            return HttpResponse("Missing comment ID", status=400)
        try:
            comment_pk = int(comment_pk)
        except (ValueError, TypeError):
            return HttpResponse("Invalid comment ID", status=400)
        issue_ct = _get_issue_ct()
        comment = get_object_or_404(Comment, pk=comment_pk, content_type=issue_ct, object_id=issue.pk)
        if request.user.username != comment.author:
            return HttpResponse("Cannot delete this comment", status=403)
        try:
            show = comment.parent.pk
        except (AttributeError, Comment.DoesNotExist):
            show = -1
        comment.delete()
        all_comment = Comment.objects.filter(content_type=issue_ct, object_id=issue.pk).select_related("parent")
        return render(
            request,
            "comments.html",
            {
                "all_comment": all_comment,
                "user": request.user,
                "show": show,
            },
        )
    return HttpResponse("Method not allowed", status=405)


@login_required(login_url="/accounts/login/")
def edit_comment(request, pk):
    if request.method == "POST":
        issue = get_object_or_404(Issue, pk=pk)
        comment_pk = request.POST.get("comment_pk")
        if not comment_pk:
            return HttpResponse("Missing comment ID", status=400)
        try:
            comment_pk = int(comment_pk)
        except (ValueError, TypeError):
            return HttpResponse("Invalid comment ID", status=400)
        issue_ct = _get_issue_ct()
        comment = get_object_or_404(Comment, pk=comment_pk, content_type=issue_ct, object_id=issue.pk)
        if request.user.username != comment.author:
            return HttpResponse("Cannot edit this comment", status=403)
        text = request.POST.get("text_comment")
        if not text:
            return HttpResponse("Missing comment text", status=400)
        comment.text = escape(text)
        comment.save()
        all_comment = Comment.objects.filter(content_type=issue_ct, object_id=issue.pk).select_related("parent")
        return render(
            request,
            "comments.html",
            {"all_comment": all_comment, "user": request.user},
        )
    return HttpResponse("Method not allowed", status=405)


@login_required(login_url="/accounts/login/")
def reply_comment(request, pk):
    if request.method == "POST":
        issue = get_object_or_404(Issue, pk=pk)
        issue_ct = _get_issue_ct()
        parent_id = request.POST.get("parent_id")
        if not parent_id:
            return HttpResponse("Missing parent comment ID", status=400)
        try:
            parent_id = int(parent_id)
        except (ValueError, TypeError):
            return HttpResponse("Invalid parent comment ID", status=400)
        parent_obj = get_object_or_404(Comment, pk=parent_id, content_type=issue_ct, object_id=issue.pk)
        reply_text = request.POST.get("text_comment")
        if not reply_text:
            return HttpResponse("Missing comment text", status=400)
        reply_text = escape(reply_text)
        author = request.user.username
        author_url = f"/profile/{request.user.username}"
        comment = Comment(
            author=author,
            author_url=author_url,
            content_type=issue_ct,
            object_id=issue.pk,
            text=reply_text,
            parent=parent_obj,
        )
        comment.save()
        all_comment = Comment.objects.filter(content_type=issue_ct, object_id=issue.pk).select_related("parent")
        return render(
            request,
            "comments.html",
            {"all_comment": all_comment, "user": request.user, "show": parent_id},
        )
    return HttpResponse("Method not allowed", status=405)


@login_required(login_url="/accounts/login/")
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
