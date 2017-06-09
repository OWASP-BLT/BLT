from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponseRedirect, HttpResponse
from .models import Comment
from website.models import Issue,UserProfile
from django.shortcuts import render, get_object_or_404
import os

@login_required(login_url="/accounts/login/")
def AddComment(request,pk):
    issue = get_object_or_404(Issue,pk=pk)
    if request.method == "POST":
        author = request.user.username
        author_url = os.path.join('/profile/',request.user.username)
        issue = issue
        text=request.POST.get('text_comment')
        comment =Comment(author=author, author_url=author_url, issue=issue, text=text)
        comment.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required(login_url="/accounts/login/")
def DeleteComment(request,pk):
    comment = get_object_or_404(Comment,pk=pk)
    if request.user.username!=comment.author:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
    comment.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required(login_url="/accounts/login/")
def EditComment(request,pk):
    comment = get_object_or_404(Comment,pk=pk)
    if request.user.username!=comment.author:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))    
    if request.method == "POST":
        comment.text=request.POST.get('new_comment')
        comment.save()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER'))


@login_required(login_url="/account/login/")
def EditCommentPage(request,pk):
    comment = get_object_or_404(Comment,pk=pk)
    if request.user.username!=comment.author:
        return HttpResponse("Can't Edit this comment")
    return render(request,'edit_comment.html',{'comment':comment})
