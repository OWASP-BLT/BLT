import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from website.models import Course, Lecture, Section, Tag, UserProfile


@login_required(login_url="/accounts/login")
def instructor_dashboard(request):
    template = "bltv/instructor_dashboard.html"
    tags = Tag.objects.all()
    user_profile = request.user.userprofile
    courses = Course.objects.filter(instructor=user_profile)
    context = {"tags": tags, "courses": courses}
    return render(request, template, context)


def edit_course(request, course_id):
    template = "bltv/dashboard_edit_course.html"
    tags = Tag.objects.all()
    try:
        course = Course.objects.get(id=course_id)
        context = {"course": course, "tags": tags}
        return render(request, template, context)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "message": "Course not found"}, status=404)


def view_course(request, course_id):
    template = "bltv/view_course.html"
    course = get_object_or_404(Course, id=course_id)
    context = {"course": course}
    return render(request, template, context)


@login_required
def course_content_management(request, course_id):
    """View for managing course content (sections and lectures)"""
    course = get_object_or_404(Course, id=course_id)

    if request.user != course.instructor.user:
        return JsonResponse({"Error": "You do not have permission to access this page."})

    next_section_order = course.sections.count() + 1

    lecture_types = Lecture.CONTENT_TYPES

    context = {
        "course": course,
        "next_section_order": next_section_order,
        "lecture_types": lecture_types,
    }

    return render(request, "bltv/content_management.html", context)


# Section CRUD operations
@login_required
@require_POST
def add_section(request, course_id):
    """Add a new section to the course"""
    course = get_object_or_404(Course, id=course_id)

    # Check permissions

    title = request.POST.get("title")
    order = int(request.POST.get("order", 0))

    section = Section.objects.create(course=course, title=title, order=order)

    return redirect("course_content_management", course_id=course_id)


@login_required
@require_POST
def edit_section(request, section_id):
    """Edit an existing section"""
    section = get_object_or_404(Section, id=section_id)
    course_id = section.course.id

    # Check permissions

    section.title = request.POST.get("title")
    section.description = request.POST.get("description")
    section.save()

    return redirect("course_content_management", course_id=course_id)


@login_required
def delete_section(request, section_id):
    """Delete a section and all its lectures"""
    section = get_object_or_404(Section, id=section_id)
    course_id = section.course.id

    # Check permissions

    section.delete()

    # Re-order remaining sections
    for i, section in enumerate(Section.objects.filter(course_id=course_id), 1):
        section.order = i
        section.save()

    return redirect("course_content_management", course_id=course_id)


# Lecture CRUD operations
@login_required
@require_POST
def add_lecture(request, section_id):
    """Add a new lecture to a section"""
    first_section = Section.objects.all().first()
    print("Section id found: ", first_section.id)
    print("Request id: ", section_id)
    section = get_object_or_404(Section, id=section_id)
    course_id = section.course.id

    # Check permissions

    # Get form data
    title = request.POST.get("title")
    content_type = request.POST.get("content_type")
    description = request.POST.get("description")
    order = int(request.POST.get("order", 0))
    duration = request.POST.get("duration") or None

    # Create base lecture
    lecture = Lecture(
        title=title, section=section, content_type=content_type, order=order, description=description, duration=duration
    )

    # Add content type specific data
    if content_type == "VIDEO":
        lecture.video_url = request.POST.get("video_url")
        lecture.content = request.POST.get("content")
    elif content_type == "LIVE":
        lecture.live_url = request.POST.get("live_url")
        lecture.scheduled_time = request.POST.get("scheduled_time") or None
    elif content_type == "DOCUMENT":
        lecture.content = request.POST.get("content")

    lecture.save()

    return redirect("course_content_management", course_id=course_id)


@login_required
@require_POST
def edit_lecture(request, lecture_id):
    """Edit an existing lecture"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    course_id = lecture.section.course.id

    # Check permissions

    # Update basic fields
    lecture.title = request.POST.get("title")
    lecture.content_type = request.POST.get("content_type")
    lecture.duration = request.POST.get("duration") or None

    # Update content type specific fields
    if lecture.content_type == "VIDEO":
        lecture.video_url = request.POST.get("video_url")
        # Clear other fields
        lecture.live_url = None
        lecture.scheduled_time = None
        lecture.recording_url = None
        lecture.content = ""
    elif lecture.content_type == "LIVE":
        lecture.live_url = request.POST.get("live_url")
        lecture.scheduled_time = request.POST.get("scheduled_time") or None
        lecture.recording_url = request.POST.get("recording_url")
        # Clear other fields
        lecture.video_url = None
        lecture.content = ""
    elif lecture.content_type == "DOCUMENT":
        lecture.content = request.POST.get("content")
        # Clear other fields
        lecture.video_url = None
        lecture.live_url = None
        lecture.scheduled_time = None
        lecture.recording_url = None

    lecture.save()

    return redirect("course_content_management", course_id=course_id)


@login_required
def delete_lecture(request, lecture_id):
    """Delete a lecture"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    section = lecture.section
    course_id = section.course.id

    # Check permissions

    lecture.delete()

    # Re-order remaining lectures in this section
    for i, lec in enumerate(Lecture.objects.filter(section=section), 1):
        lec.order = i
        lec.save()

    return redirect("course_content_management", course_id=course_id)


# API endpoints for AJAX operations
@login_required
@require_GET
def get_lecture_data(request, lecture_id):
    """API endpoint to get lecture data for editing"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

    # Check permissions

    data = {
        "id": lecture.id,
        "title": lecture.title,
        "content_type": lecture.content_type,
        "video_url": lecture.video_url,
        "live_url": lecture.live_url,
        "scheduled_time": lecture.scheduled_time.isoformat() if lecture.scheduled_time else None,
        "recording_url": lecture.recording_url,
        "content": lecture.content,
        "duration": lecture.duration,
        "order": lecture.order,
    }

    return JsonResponse(data)


@login_required
@require_GET
def get_section_data(request, section_id):
    """API endpoint to get lecture data for editing"""
    section = get_object_or_404(Section, id=section_id)

    # Check permissions

    data = {"id": section.id, "title": section.title, "description": section.description}

    return JsonResponse(data)


@login_required
@require_POST
def update_sections_order(request, course_id):
    """API endpoint to update the order of sections"""
    course = get_object_or_404(Course, id=course_id)

    # Check permissions

    try:
        data = json.loads(request.body)
        sections = data.get("sections", [])

        for section_data in sections:
            section_id = section_data.get("id")
            new_order = section_data.get("order")

            section = get_object_or_404(Section, id=section_id, course=course)
            section.order = new_order
            section.save()

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


@login_required
@require_POST
def update_lectures_order(request, section_id):
    """API endpoint to update the order of lectures within a section"""
    section = get_object_or_404(Section, id=section_id)

    # Check permissions

    try:
        data = json.loads(request.body)
        lectures = data.get("lectures", [])

        for lecture_data in lectures:
            lecture_id = lecture_data.get("id")
            new_order = lecture_data.get("order")

            lecture = get_object_or_404(Lecture, id=lecture_id, section=section)
            lecture.order = new_order
            lecture.save()

        return JsonResponse({"status": "success"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=400)


def get_course_content(request, course_id):
    if request.method == "GET":
        course = get_object_or_404(Course, id=course_id)
        sections = course.sections.all().order_by("order")

        return render(
            request,
            "bltv/includes/view_course_content.html",
            {"course": course, "sections": sections},
        )


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
