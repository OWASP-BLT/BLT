import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from website.decorators import instructor_required
from website.models import Course, Enrollment, Lecture, LectureStatus, Section, Tag, UserProfile


def education_home(request):
    template = "education/education.html"
    user = request.user
    if user.is_authenticated:
        is_instructor = (
            Course.objects.filter(instructor__user=user).exists()
            or Lecture.objects.filter(section__course__instructor__user=user).exists()
        )
    else:
        is_instructor = False

    featured_lectures = Lecture.objects.filter(section__isnull=True)
    courses = Course.objects.all()
    context = {"is_instructor": is_instructor, "featured_lectures": featured_lectures, "courses": courses}
    return render(request, template, context)


@login_required(login_url="/accounts/login")
def instructor_dashboard(request):
    template = "education/instructor_dashboard.html"
    tags = Tag.objects.all()
    user_profile = request.user.userprofile
    courses = Course.objects.filter(instructor=user_profile)
    standalone_lectures = Lecture.objects.filter(instructor=user_profile, section__isnull=True)
    context = {"tags": tags, "courses": courses, "standalone_lectures": standalone_lectures}
    return render(request, template, context)


@instructor_required
def edit_course(request, course_id):
    template = "education/dashboard_edit_course.html"
    tags = Tag.objects.all()
    try:
        course = Course.objects.get(id=course_id)
        context = {"course": course, "tags": tags}
        return render(request, template, context)
    except Course.DoesNotExist:
        return JsonResponse({"success": False, "message": "Course not found"}, status=404)


@login_required(login_url="/accounts/login")
def enroll(request, course_id):
    course = get_object_or_404(Course, id=course_id)
    userprofile = request.user.userprofile

    enrollment, created = Enrollment.objects.get_or_create(student=userprofile, course=course)

    if created:
        message = "You have been successfully enrolled in the course."
    else:
        message = "You are already enrolled in this course."

    messages.success(request, message)
    return redirect("study_course", course_id=course_id)


def view_course(request, course_id):
    template = "education/view_course.html"
    course = get_object_or_404(Course, id=course_id)
    context = {
        "course": course,
    }
    return render(request, template, context)


@login_required(login_url="/accounts/login")
def view_lecture(request, lecture_id):
    template = "education/view_lecture.html"
    lecture = get_object_or_404(Lecture, id=lecture_id)
    context = {
        "lecture": lecture,
    }
    return render(request, template, context)


@login_required(login_url="/accounts/login")
def create_standalone_lecture(request):
    template = "education/create_standalone_lecture.html"
    return render(request, template)


@login_required(login_url="/accounts/login")
def edit_standalone_lecture(request, lecture_id):
    template = "education/edit_standalone_lecture.html"
    lecture = get_object_or_404(Lecture, id=lecture_id)
    context = {"lecture": lecture}
    return render(request, template, context)


@login_required(login_url="/accounts/login")
def study_course(request, course_id):
    template = "education/study_course.html"

    course = get_object_or_404(Course, id=course_id)

    userprofile = request.user.userprofile
    enrollment = Enrollment.objects.filter(student=userprofile, course=course).first()

    if not enrollment:
        messages.error(request, "You are not enrolled in this course.")
        return redirect("education")

    course_progress = enrollment.calculate_progress()

    sections = (
        Section.objects.filter(course=course)
        .prefetch_related(Prefetch("lectures", queryset=Lecture.objects.all().order_by("order")))
        .order_by("order")
    )

    lecture_statuses = {
        status.lecture_id: status.status
        for status in LectureStatus.objects.filter(student=userprofile, lecture__section__course=course)
    }

    # Get the first incomplete lecture for initial display
    current_lecture = None
    for section in sections:
        for lecture in section.lectures.all():
            lecture_status = lecture_statuses.get(lecture.id, None)
            if lecture_status != "COMPLETED":
                current_lecture = lecture
                break
        if current_lecture:
            break

    # If all lectures are complete or none started, show the first lecture
    if not current_lecture and sections.exists() and sections.first().lectures.exists():
        current_lecture = sections.first().lectures.first()

    context = {
        "course": course,
        "sections": sections,
        "course_progress": course_progress,
        "lecture_statuses": lecture_statuses,
        "current_lecture": current_lecture,
        "now": timezone.now(),
    }

    return render(request, template, context)


@login_required(login_url="/accounts/login")
def mark_lecture_complete(request):
    """API endpoint to mark a lecture as completed"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            lecture_id = data.get("lecture_id")

            if not lecture_id:
                return JsonResponse({"success": False, "error": "Lecture ID is required"})

            lecture = get_object_or_404(Lecture, id=lecture_id)
            userprofile = request.user.userprofile

            course = lecture.section.course
            enrollment = Enrollment.objects.filter(student=userprofile, course=course).first()
            if not enrollment:
                return JsonResponse({"success": False, "error": "You are not enrolled in this course."})

            lecture_status, created = LectureStatus.objects.update_or_create(
                student=userprofile, lecture=lecture, defaults={"status": "COMPLETED"}
            )

            progress = enrollment.calculate_progress()

            return JsonResponse({"success": True, "status": "COMPLETED", "progress": progress})

        except Exception as e:
            print("Error: ", str(e))
            return JsonResponse({"status": "error", "message": "An error occured, please try again later"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method"})


@instructor_required
def course_content_management(request, course_id):
    """View for managing course content (sections and lectures)"""
    course = get_object_or_404(Course, id=course_id)

    next_section_order = course.sections.count() + 1

    lecture_types = Lecture.CONTENT_TYPES

    context = {
        "course": course,
        "next_section_order": next_section_order,
        "lecture_types": lecture_types,
    }

    return render(request, "education/content_management.html", context)


# Section CRUD operations
@instructor_required
@require_POST
def add_section(request, course_id):
    """Add a new section to the course"""
    course = get_object_or_404(Course, id=course_id)

    title = request.POST.get("title")
    order = int(request.POST.get("order", 0))

    section = Section.objects.create(course=course, title=title, order=order)
    messages.success(request, f"Section '{title}' was added successfully!")

    return redirect("course_content_management", course_id=course_id)


@instructor_required
@require_POST
def edit_section(request, section_id):
    """Edit an existing section"""
    section = get_object_or_404(Section, id=section_id)
    course_id = section.course.id

    section.title = request.POST.get("title")
    section.description = request.POST.get("description")
    section.save()

    messages.success(request, f"Section '{section.title}' was edited successfully!")

    return redirect("course_content_management", course_id=course_id)


@instructor_required
def delete_section(request, section_id):
    """Delete a section and all its lectures"""
    section = get_object_or_404(Section, id=section_id)
    course_id = section.course.id

    section.delete()

    # Re-order remaining sections
    for i, section in enumerate(Section.objects.filter(course_id=course_id), 1):
        section.order = i
        section.save()

    messages.success(request, "Section was deleted successfully!")

    return redirect("course_content_management", course_id=course_id)


# Lecture CRUD operations
@require_POST
def add_lecture(request, section_id):
    """Add a new lecture to a section, else standalone"""
    print("Section ID:", section_id, type(section_id))
    if section_id == 0:
        section = None
    else:
        section = get_object_or_404(Section, id=section_id)
        course_id = section.course.id

    user_profile = request.user.userprofile
    title = request.POST.get("title")
    content_type = request.POST.get("content_type")
    description = request.POST.get("description")
    order = int(request.POST.get("order", 0))
    duration = request.POST.get("duration") or None

    lecture = Lecture(
        title=title,
        instructor=user_profile,
        section=section,
        content_type=content_type,
        order=order,
        description=description,
        duration=duration,
    )

    if content_type == "VIDEO":
        lecture.video_url = request.POST.get("video_url")
        lecture.content = request.POST.get("content")
        lecture.generate_transcript_and_quiz()
    elif content_type == "LIVE":
        lecture.live_url = request.POST.get("live_url")
        lecture.scheduled_time = request.POST.get("scheduled_time") or None
    elif content_type == "DOCUMENT":
        lecture.content = request.POST.get("content")

    lecture.save()

    messages.success(request, f"Lecture '{title}' was added successfully!")

    if section:
        return redirect("course_content_management", course_id=course_id)
    else:
        return redirect("instructor_dashboard")


@instructor_required
@require_POST
def edit_lecture(request, lecture_id):
    """Edit an existing lecture"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

    is_standalone = True
    if lecture.section:
        is_standalone = False
        course_id = lecture.section.course.id

    lecture.title = request.POST.get("title")
    lecture.content_type = request.POST.get("content_type")
    lecture.description = request.POST.get("description")
    lecture.content = request.POST.get("content", "")
    lecture.duration = request.POST.get("duration") or None

    if lecture.content_type == "VIDEO":
        lecture.video_url = request.POST.get("video_url")
        lecture.live_url = None
        lecture.scheduled_time = None
        lecture.recording_url = None
        lecture.generate_transcript_and_quiz()
    elif lecture.content_type == "LIVE":
        lecture.live_url = request.POST.get("live_url")
        lecture.scheduled_time = request.POST.get("scheduled_time") or None
        lecture.recording_url = request.POST.get("recording_url")
        lecture.video_url = None
    elif lecture.content_type == "DOCUMENT":
        lecture.video_url = None
        lecture.live_url = None
        lecture.scheduled_time = None
        lecture.recording_url = None

    lecture.save()
    messages.success(request, f"Lecture '{lecture.title}' was edited successfully!")

    if is_standalone:
        return redirect("view_lecture", lecture_id)
    else:
        return redirect("course_content_management", course_id=course_id)


@instructor_required
def delete_lecture(request, lecture_id):
    """Delete a lecture"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    section = lecture.section
    course_id = section.course.id

    lecture.delete()

    for i, lec in enumerate(Lecture.objects.filter(section=section), 1):
        lec.order = i
        lec.save()

    messages.success(request, f"Lecture '{lecture.title}' was deleted successfully!")

    return redirect("course_content_management", course_id=course_id)


@instructor_required
@require_GET
def get_lecture_data(request, lecture_id):
    """API endpoint to get lecture data for editing"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

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
        "description": lecture.description,
        "order": lecture.order,
    }

    return JsonResponse(data)


@instructor_required
@require_GET
def get_section_data(request, section_id):
    """API endpoint to get lecture data for editing"""
    section = get_object_or_404(Section, id=section_id)

    data = {"id": section.id, "title": section.title, "description": section.description}

    return JsonResponse(data)


@instructor_required
@require_POST
def update_sections_order(request, course_id):
    """API endpoint to update the order of sections"""
    course = get_object_or_404(Course, id=course_id)

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
        print("Error: ", str(e))
        return JsonResponse({"status": "error", "message": "An error occured, please try again later"}, status=400)


@instructor_required
@require_POST
def update_lectures_order(request, section_id):
    """API endpoint to update the order of lectures within a section"""
    section = get_object_or_404(Section, id=section_id)

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
        print("Error: ", str(e))
        return JsonResponse({"status": "error", "message": "An error occured, please try again later"}, status=400)


def get_course_content(request, course_id):
    if request.method == "GET":
        course = get_object_or_404(Course, id=course_id)
        sections = course.sections.all().order_by("order")

        is_enrolled = False
        is_completed = False
        course_progress = 0.0

        if request.user.is_authenticated:
            userprofile = request.user.userprofile
            enrollment = Enrollment.objects.filter(student=userprofile, course=course).first()
            if enrollment:
                is_enrolled = True
                is_completed = enrollment.completed
                course_progress = enrollment.calculate_progress()

        return render(
            request,
            "education/includes/view_course_content.html",
            {
                "course": course,
                "sections": sections,
                "is_enrolled": is_enrolled,
                "is_completed": is_completed,
                "course_progress": course_progress,
            },
        )


@require_POST
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
