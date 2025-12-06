import json
import logging
import os
import re
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from website.decorators import instructor_required
from website.forms import VideoSubmissionForm
from website.models import Course, EducationalVideo, Enrollment, Lecture, LectureStatus, Section, Tag, UserProfile
from website.utils import validate_file_type

logger = logging.getLogger(__name__)


def is_valid_url(url, url_type):
    """Helper function to validate URLs based on their type."""
    if url_type == "video":
        allowed_domains = {"www.youtube.com", "youtube.com", "youtu.be", "vimeo.com", "www.vimeo.com"}
    elif url_type == "live":
        allowed_domains = {"zoom.us", "meet.google.com", "vimeo.com", "www.vimeo.com"}
    else:
        return False

    parsed_url = urlparse(url)
    return parsed_url.netloc in allowed_domains


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
            logger.error(f"Error: {str(e)}")
            return JsonResponse({"status": "error", "message": "An error occurred, please try again later"}, status=400)

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


@instructor_required
@require_POST
def add_section(request, course_id):
    """Add a new section to the course"""
    course = get_object_or_404(Course, id=course_id)

    # Sanitize user input
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

    # Sanitize user input
    section.title = request.POST.get("title")
    section.description = request.POST.get("description")
    section.save()

    messages.success(request, f"Section '{section.title}' was edited successfully!")

    return redirect("course_content_management", course_id=course_id)


@instructor_required
@require_POST
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
        video_url = request.POST.get("video_url")
        if not is_valid_url(video_url, "video"):
            messages.error(request, "Only YouTube and Vimeo URLs are allowed for video lectures.")
            if section_id == 0:
                return redirect("create_standalone_lecture")
            else:
                return redirect("create_standalone_lecture", course_id=course_id)
        lecture.video_url = video_url
        lecture.content = request.POST.get("content")
    elif content_type == "LIVE":
        live_url = request.POST.get("live_url")
        if not is_valid_url(live_url, "live"):
            messages.error(request, "Only Zoom, Google Meet or Vimeo URLs are allowed for live lectures.")
            if section_id == 0:
                return redirect("create_standalone_lecture")
            else:
                return redirect("create_standalone_lecture", course_id=course_id)
        lecture.live_url = live_url
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
    lecture = get_object_or_404(Lecture, id=lecture_id)

    is_standalone = True
    if lecture.section:
        is_standalone = False
        course_id = lecture.section.course.id

    lecture.title = request.POST.get("title", "")
    lecture.content_type = request.POST.get("content_type", "")
    lecture.description = request.POST.get("description", "")
    lecture.content = request.POST.get("content", "")
    lecture.duration = request.POST.get("duration", "") or None

    if lecture.content_type == "VIDEO":
        video_url = request.POST.get("video_url", "")
        if not is_valid_url(video_url, "youtube"):
            messages.error(request, "Only YouTube URLs are allowed for video lectures.")
            if is_standalone:
                return redirect("view_lecture", lecture_id)
            else:
                return redirect("course_content_management", course_id=course_id)
        lecture.video_url = video_url
        lecture.live_url = None
        lecture.scheduled_time = None
        lecture.recording_url = None
    elif lecture.content_type == "LIVE":
        lecture.live_url = request.POST.get("live_url", "")
        lecture.scheduled_time = request.POST.get("scheduled_time", "") or None
        lecture.recording_url = request.POST.get("recording_url", "")
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
        logger.error(f"Error: {str(e)}")
        return JsonResponse({"status": "error", "message": "An error occurred, please try again later"}, status=400)


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
        logger.error(f"Error: {str(e)}")
        return JsonResponse({"status": "error", "message": "An error occurred, please try again later"}, status=400)


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
            if thumbnail:
                is_valid, error_message = validate_file_type(
                    request,
                    "thumbnail",
                    allowed_extensions=["jpg", "jpeg", "png"],
                    allowed_mime_types=["image/jpeg", "image/png"],
                    max_size=5 * 1024 * 1024,  # 5MB
                )
                if not is_valid:
                    return JsonResponse({"success": False, "message": error_message}, status=400)
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
        logger.error(f"Error in create_or_update_course: {e}")
        return JsonResponse({"success": False, "message": "An error occurred. Please try again later."}, status=500)


@login_required(login_url="/accounts/login")
@require_POST
def add_video(request):
    try:
        form = VideoSubmissionForm(request.POST)
        if form.is_valid():
            video_url = form.cleaned_data["video_url"]

            # Parse and validate the URL
            try:
                parsed_url = urlparse(video_url)
                hostname = parsed_url.hostname or ""
                # Check if hostname contains youtube.com, youtu.be or vimeo.com
                if not any(domain in hostname for domain in ["youtube.com", "youtu.be", "vimeo.com"]):
                    return JsonResponse(
                        {"success": False, "message": "Only YouTube or Vimeo URLs are allowed."}, status=400
                    )
            except Exception:
                return JsonResponse({"success": False, "message": "Invalid URL format."}, status=400)

            # Fetch the video title and description
            video_data = fetch_video_data(video_url)
            if not video_data:
                return JsonResponse(
                    {"success": False, "message": "Failed to fetch video data. Please check the URL and try again."},
                    status=400,
                )

            # Check if the video is educational
            if not is_educational_video(video_data["title"], video_data["description"]):
                return JsonResponse(
                    {"success": False, "message": "The video does not appear to be educational content."}, status=400
                )

            # Save the video details to the database
            EducationalVideo.objects.create(
                url=video_url,
                title=video_data["title"],
                description=video_data["description"],
                is_educational=True,
                submitted_by=request.user,
            )

            return JsonResponse({"success": True, "message": "Video added successfully."}, status=201)

        # Form validation errors
        errors = dict(form.errors.items())
        error_message = next(iter(errors.values()))[0] if errors else "Invalid form data."
        return JsonResponse({"success": False, "message": error_message}, status=400)
    except Exception as e:
        logger.error(f"Error in add_video: {str(e)}")
        return JsonResponse({"success": False, "message": "An unexpected error occurred."}, status=500)


def fetch_video_data(video_url):
    parsed_url = urlparse(video_url)
    host = parsed_url.hostname
    if host and (host.endswith("youtube.com") or host == "youtu.be"):
        return fetch_youtube_video_data(video_url)
    elif host and (host == "vimeo.com" or host.endswith(".vimeo.com")):
        return fetch_vimeo_video_data(video_url)
    return None


def fetch_youtube_video_data(video_url):
    api_key = os.environ.get("YOUTUBE_API_KEY", getattr(settings, "YOUTUBE_API_KEY", None))
    if not api_key:
        logger.error("YouTube API key is missing")
        return None

    video_id = extract_youtube_video_id(video_url)
    if not video_id:
        logger.warning(f"Could not extract YouTube video ID from URL: {video_url}")
        return None

    api_url = f"https://www.googleapis.com/youtube/v3/videos?id={video_id}&key={api_key}&part=snippet"
    try:
        response = requests.get(api_url, timeout=10)
        if response.status_code != 200:
            logger.error(f"YouTube API error: {response.status_code}")
            return None

        data = response.json()
        if "items" not in data or not data["items"]:
            logger.warning(f"No video data found for YouTube video ID: {video_id}")
            return None

        snippet = data["items"][0]["snippet"]
        return {"title": snippet["title"], "description": snippet["description"]}
    except Exception as e:
        logger.error(f"Error fetching YouTube data: {str(e)}")
        return None


def extract_youtube_video_id(video_url):
    # Handle youtu.be/VIDEO_ID format
    if "youtu.be" in video_url:
        match = re.search(r"youtu\.be\/([0-9A-Za-z_-]{11})", video_url)
        if match:
            return match.group(1)

    # Handle youtube.com/watch?v=VIDEO_ID format
    match = re.search(r"(?:v=)([0-9A-Za-z_-]{11})", video_url)
    if match:
        return match.group(1)

    # Handle youtube.com/embed/VIDEO_ID format
    match = re.search(r"(?:embed\/)([0-9A-Za-z_-]{11})", video_url)
    if match:
        return match.group(1)

    return None


def fetch_vimeo_video_data(video_url):
    video_id = extract_vimeo_video_id(video_url)
    if not video_id:
        logger.warning(f"Could not extract Vimeo video ID from URL: {video_url}")
        return None

    api_url = f"https://api.vimeo.com/videos/{video_id}"
    access_token = os.environ.get("VIMEO_ACCESS_TOKEN", getattr(settings, "VIMEO_ACCESS_TOKEN", None))
    if not access_token:
        logger.error("Vimeo access token is missing")
        return None

    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(api_url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(
                f"Vimeo API error: {response.status_code} - {response.text if hasattr(response, 'text') else ''}"
            )
            return None

        data = response.json()
        return {"title": data["name"], "description": data["description"]}
    except Exception as e:
        logger.error(f"Error fetching Vimeo data: {str(e)}")
        return None


def extract_vimeo_video_id(video_url):
    match = re.search(r"vimeo\.com\/(\d+)", video_url)
    return match.group(1) if match else None


def is_educational_video(title, description):
    openai_api_key = os.environ.get("OPENAI_API_KEY", getattr(settings, "OPENAI_API_KEY", None))

    if not openai_api_key:
        logger.warning("OpenAI API key is missing, falling back to keyword-based validation")
        # Fallback to basic keyword checking if API key is not available
        educational_keywords = [
            "learn",
            "education",
            "tutorial",
            "how to",
            "course",
            "lesson",
            "training",
            "skills",
            "knowledge",
            "academic",
        ]
        content = (title + " " + description).lower()
        for keyword in educational_keywords:
            if keyword in content:
                return True
        return False

    prompt = f"Is the following video educational?\n\nTitle: {title}\n\nDescription: {description}\n\nAnswer with 'yes' or 'no'."
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_api_key}"},
            json={
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "system",
                        "content": "You determine if content is educational. Respond with only 'yes' or 'no'.",
                    },
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 5,
            },
            timeout=10,
        )
        if response.status_code != 200:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return False

        answer = response.json()["choices"][0]["message"]["content"].strip().lower()
        return answer == "yes"
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        return False
