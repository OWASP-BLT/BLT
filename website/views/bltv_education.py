from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from website.models import Course, Tag, UserProfile


def instructor_dashboard(request):
    template = "bltv/instructor_dashboard.html"
    tags = Tag.objects.all()
    user_profile = request.user.userprofile
    courses = Course.objects.filter(instructor=user_profile)
    context = {"tags": tags, "courses": courses}
    return render(request, template, context)


def edit_course(request, course_id):
    template = "bltv/edit_course.html"
    tags = Tag.objects.all()
    try:
        course = Course.objects.get(id=course_id)
        context = {"course": course, "tags": tags}
        return render(request, template, context)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "message": "Course not found"}, status=404)


@require_POST
@login_required(login_url="/accounts/login")
def create_or_update_course(request):
    try:
        if request.method == "POST":
            title = request.POST.get("title")
            description = request.POST.get("description")
            level = request.POST.get("level", "BEG")
            tag_ids = request.POST.getlist("tags")
            thumbnail = request.FILES.get("thumbnail")

            if not title or not description:
                missing_fields = []
                if not title:
                    missing_fields.append("Course title")
                if not description:
                    missing_fields.append("Course description")
                return JsonResponse(
                    {"success": False, "message": f"{', '.join(missing_fields)} is required"}, status=400
                )

            user = request.user
            user_profile = UserProfile.objects.get(user=user)

            course_id = request.POST.get("id")
            if course_id:
                try:
                    course = Course.objects.get(id=course_id)
                except Course.DoesNotExist:
                    return JsonResponse({"success": False, "message": "Course not found"}, status=404)
            else:
                course = Course()

            course.title = title
            course.description = description
            course.instructor = user_profile
            course.level = level
            if thumbnail:
                course.thumbnail = thumbnail

            course.save()

            tags = Tag.objects.filter(id__in=tag_ids)
            course.tags.set(tags)

            return JsonResponse(
                {
                    "success": True,
                    "message": "Course created/updated successfully",
                    "course_id": course.id,
                },
                status=201,
            )
        else:
            return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)
    except Exception as e:
        print(f"Error in create_or_update_course: {e}")
        return JsonResponse({"success": False, "message": "An error occurred. Please try again later."}, status=500)
