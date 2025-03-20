import markdown
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.contenttypes.models import ContentType
from django.utils.text import slugify
from django.views import generic

from website.models import Post


class PostListView(generic.ListView):
    model = Post
    template_name = "blog/post_list.html"
    context_object_name = "posts"
    paginate_by = 5


class PostDetailView(generic.DetailView):
    model = Post
    template_name = "blog/post_detail.html"

    def get_object(self):
        post = super().get_object()
        post.content = markdown.markdown(post.content)
        return post

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["content_type"] = ContentType.objects.get_for_model(Post).model
        context["all_comment"] = self.object.comments.all()
        return context


class PostCreateView(LoginRequiredMixin, generic.CreateView):
    model = Post
    fields = ["title", "content", "image"]
    template_name = "blog/post_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user

        base_slug = slugify(form.instance.title)
        slug = base_slug
        counter = 1
        if slug == "new":
            slug = f"{base_slug}-{counter}"
            counter += 1
        while Post.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        form.instance.slug = slug

        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, generic.UpdateView):
    model = Post
    fields = ["title", "content", "image"]
    template_name = "blog/post_form.html"

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, generic.DeleteView):
    model = Post
    template_name = "blog/post_delete.html"
    success_url = "/blog"

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
