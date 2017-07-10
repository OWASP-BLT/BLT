from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import HttpResponseRedirect, HttpResponse
from .models import Comment
from website.models import Issue,UserProfile
from django.shortcuts import render, get_object_or_404
import os

@login_required(login_url='/accounts/login/')
def add_comment(request):
    pass
    issue = Issue.objects.get(pk=request.POST.get('issue_pk'))
    if request.method == "POST":
        author = request.user.username
        author_url = os.path.join('/profile/',request.user.username)
        issue = issue
        text=request.POST.get('text_comment')
        comment =Comment(author=author, author_url=author_url, issue=issue, text=text)
        comment.save()
        all_comment = Comment.objects.filter(issue=issue)
    return render(request,'comments.html',{'all_comment':all_comment,
                                            'user':request.user},)   


@login_required(login_url='/accounts/login')
def delete_comment(request):
    if request.method=="POST":
        issue = Issue.objects.get(pk=request.POST['issue_pk'])
        all_comment = Comment.objects.filter(issue=issue)
        comment = Comment.objects.get(pk=int(request.POST['comment_pk']))
        if request.user.username!=comment.author:
            return HttpResponse("Cannot delete this comment")
        comment.delete()
    return render(request,'comments.html',{'all_comment':all_comment,
                                            'user':request.user},) 



@login_required(login_url="/accounts/login/")
def EditComment(request,pk):
    comment = get_object_or_404(Comment,pk=pk)
    if request.user.username!=comment.author:
        return HttpResponseRedirect(os.path.join('/issue',str(pk)))    
    if request.method == "POST":
        comment.text=request.POST.get('new_comment')
        comment.save()
    return HttpResponseRedirect(os.path.join('/issue',str(comment.issue.pk)))

@login_required(login_url="/account/login/")
def EditCommentPage(request,pk):
    comment = get_object_or_404(Comment,pk=pk)
    if request.user.username!=comment.author:
        return HttpResponse("Can't Edit this comment")
    return render(request,'edit_comment.html',{'comment':comment})
