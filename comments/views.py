from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponseRedirect, HttpResponse
from .models import Comment
from website.models import Issue, UserProfile
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string

import os
import json


@login_required(login_url='/accounts/login/')
def add_comment(request):
    pk = request.POST.get('issue_pk')
    issue = Issue.objects.get(pk=pk)
    if request.method == "POST":
        author = request.user.username
        author_url = os.path.join('/profile/', request.user.username)
        issue = issue
        text = request.POST.get('text_comment')
        user_list = []
        temp_text = text.split()
        new_text = ''
        new_msg = ''
        for item in temp_text:
            msg = item
            if item[0] == "@":
                if User.objects.filter(username=item[1:]).exists():
                    user = User.objects.get(username=item[1:])
                    user_list.append(user)
                    msg = user.username
                    item = "<a href='/profile/{0}'>@{1}</a>".format(
                        item[1:], item[1:])

            new_text = new_text + " " + item
            new_msg  = new_msg + " " + msg

        for obj in user_list:
            msg_plain = render_to_string(
                'email/comment_mention.txt',
                {'name': obj.username, 'commentor': request.user, 'issue_pk': pk, 'comment': new_msg})
            msg_html = render_to_string(
                'email/comment_mention.txt',
                {'name': obj.username, 'commentor': request.user, 'issue_pk': pk, 'comment': new_msg})

            send_mail('You have been mentioned in a comment',
                      msg_plain,
                      'Bugheist <support@bugheist.com>',
                      [obj.email],
                      html_message=msg_html)

        comment = Comment(author=author, author_url=author_url,
                          issue=issue, text=new_text)
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(request, 'comments.html', {'all_comment': all_comment,
                                             'user': request.user},)


@login_required(login_url='/accounts/login')
def delete_comment(request):
    if request.method == "POST":
        issue = Issue.objects.get(pk=request.POST['issue_pk'])
        all_comment = Comment.objects.filter(issue=issue)
        comment = Comment.objects.get(pk=int(request.POST['comment_pk']))
        if request.user.username != comment.author:
            return HttpResponse("Cannot delete this comment")
        comment.delete()
    return render(request, 'comments.html', {'all_comment': all_comment,
                                             'user': request.user},)


@login_required(login_url="/accounts/login/")
def edit_comment(request, pk):
    if request.method == "GET":
        issue = Issue.objects.get(pk=request.GET['issue_pk'])
        comment = Comment.objects.get(pk=request.GET['comment_pk'])
        comment.text = request.GET.get('text_comment')
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(request, 'comments.html', {'all_comment': all_comment,
                                             'user': request.user},)


@login_required(login_url='/accounts/login')
def autocomplete(request):
    q_string = request.GET.get('search', '')
    if len(q_string) == 0:
        return HttpResponse(request.GET['callback'] + '(' + json.dumps([]) + ');',
                            content_type='application/json')
    q_list = q_string.split(' ')
    q_s = q_list[len(q_list) - 1]
    if len(q_s) == 0 or q_s[0] != "@":
        return HttpResponse(request.GET['callback'] + '(' + json.dumps([]) + ');',
                            content_type='application/json')

    q_s = q_s[1:]
    search_qs = User.objects.filter(username__startswith=q_s)
    results = []
    for r in search_qs:
        results.append(r.username)
    resp = request.GET['callback'] + '(' + json.dumps(results) + ');'
    return HttpResponse(resp, content_type='application/json')
