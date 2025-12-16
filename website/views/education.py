import json
import logging
import os
import re
from urllib.parse import urlparse

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST , require_http_methods

from website.decorators import instructor_required
from website.models import Course, Enrollment, Lecture, LectureStatus, Section, Tag, UserProfile
from website.utils import validate_file_type
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
from website.models import EducationalVideo, VideoQuizQuestion, QuizAttempt, Course, Lecture
from django.views.generic import DetailView
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
)


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

import os
import re
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

from website.models import (
    Course, Lecture, EducationalVideo, VideoQuizQuestion, QuizAttempt
)

# Initialize OpenAI client
openai_api_key = os.getenv('OPENAI_API_KEY')
if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
else:
    client = None


def get_youtube_transcript(youtube_id):
    """
    Fetch YouTube transcript as plain text (first ~3000 chars).
    Compatible with the current YouTubeTranscriptApi version.
    """
    try:
        print(f"DEBUG: get_youtube_transcript called for {youtube_id}")

        api = YouTubeTranscriptApi()
        transcript_list = api.list(youtube_id)      # Returns TranscriptList
        transcript_list = list(transcript_list)     # Convert to [Transcript, ...]

        # Each Transcript object has .fetch() which returns FetchedTranscriptSnippet iterable
        snippets = []
        for transcript in transcript_list:
            for snippet in transcript.fetch():
                snippets.append(snippet)

        # FetchedTranscriptSnippet has .text attribute (not ['text'] dict access)
        transcript_text = " ".join(snippet.text for snippet in snippets)

        print(f"DEBUG: transcript length for {youtube_id} = {len(transcript_text)}")
        return transcript_text[:3000]  # Limit to 3000 chars for efficiency

    except Exception as e:
        print(f"DEBUG: transcript error for {youtube_id}: {e}")
        return None


def generate_ai_summary_and_verify(youtube_id, title, transcript):
    """
    Use OpenAI to generate summary and verify if content is educational.
    Returns (summary_text, is_educational_bool).
    """
    if not client:
        print("DEBUG: OpenAI client not initialized (OPENAI_API_KEY missing)")
        return None, False

    if not openai_api_key:
        print("DEBUG: OPENAI_API_KEY is missing")
        return None, False

    if not transcript:
        print(f"DEBUG: no transcript provided for video {youtube_id}")
        return None, False

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an educational content expert. "
                        "Analyze the video transcript and determine if it's educational/security-related content. "
                        "Respond in JSON format with 'summary' and 'is_educational' fields."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Video Title: {title}\n\nTranscript:\n{transcript}\n\n"
                        "Provide a brief (100-150 word) summary and determine if this is educational security content. "
                        "Respond ONLY with valid JSON using double quotes, like this:\n"
                        '{"summary": "...", "is_educational": true}'
                    ),
                },
            ],
            max_tokens=500,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        print(f"DEBUG: raw OpenAI content for {youtube_id}: {content[:100]}...")  # First 100 chars

        # Strip code fences if model wraps JSON in ``` (triple backticks)
        content_stripped = content.strip()
        if content_stripped.startswith("```"):
            lines = content_stripped.splitlines()
            # Remove first line (opening fence)
            if len(lines) > 1:
                lines = lines[1:]
            # Remove last line if it's a closing fence
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content_stripped = "\n".join(lines).strip()

        data = json.loads(content_stripped)
        summary = data.get("summary", "")
        is_educational = data.get("is_educational", False)

        print(
            f"DEBUG: parsed summary_present={bool(summary)}, "
            f"is_educational={is_educational}"
        )
        return summary, is_educational

    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON decode error for {youtube_id}: {e}")
        print(f"DEBUG: content that failed to parse: {content_stripped[:200]}")
        return None, False
    except Exception as e:
        print(f"DEBUG: OpenAI error for {youtube_id}: {e}")
        return None, False


def generate_quiz_from_transcript(youtube_id, transcript, title):
    """
    Generate 5-10 quiz questions from transcript using OpenAI.
    Returns list of question dicts or empty list on error.
    """
    if not client:
        print(f"DEBUG: OpenAI client not initialized, skipping quiz for {youtube_id}")
        return []

    if not openai_api_key:
        print(f"DEBUG: OPENAI_API_KEY missing, skipping quiz for {youtube_id}")
        return []

    if not transcript:
        print(f"DEBUG: no transcript for quiz generation for {youtube_id}")
        return []

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a quiz generator expert. Create educational multiple-choice questions "
                        "based on the video content. Respond ONLY with valid JSON array."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Create 5 multiple-choice questions from this video on '{title}':\n\n{transcript}\n\n"
                        "Respond ONLY with valid JSON array in this exact format:\n"
                        "[\n"
                        "  {\n"
                        '    "question": "What is...?",\n'
                        '    "option_a": "Answer A",\n'
                        '    "option_b": "Answer B",\n'
                        '    "option_c": "Answer C",\n'
                        '    "option_d": "Answer D",\n'
                        '    "correct_answer": "A",\n'
                        '    "explanation": "The correct answer is..."\n'
                        "  }\n"
                        "]"
                    ),
                },
            ],
            max_tokens=2000,
            temperature=0.7,
        )

        content = response.choices[0].message.content
        print(f"DEBUG: raw quiz content for {youtube_id}: {content[:100]}...")

        # Strip code fences if present (triple backticks)
        content_stripped = content.strip()
        if content_stripped.startswith("```"):
            lines = content_stripped.splitlines()
            if len(lines) > 1:
                lines = lines[1:]
            if lines and lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            content_stripped = "\n".join(lines).strip()

        questions = json.loads(content_stripped)
        print(f"DEBUG: parsed {len(questions)} quiz questions for {youtube_id}")
        return questions[:10]  # Limit to 10 questions

    except json.JSONDecodeError as e:
        print(f"DEBUG: quiz JSON decode error for {youtube_id}: {e}")
        return []
    except Exception as e:
        print(f"DEBUG: quiz generation error for {youtube_id}: {e}")
        return []


def education_home(request):
    """
    Main education page. Displays courses, lectures, and educational videos.
    Handles YouTube video submission with AI-powered summary and quiz generation.
    """
    template = "education/education.html"
    user = request.user

    # Determine if current user is an instructor
    if user.is_authenticated:
        is_instructor = (
            Course.objects.filter(instructor__user=user).exists()
            or Lecture.objects.filter(section__course__instructor__user=user).exists()
        )
    else:
        is_instructor = False

    # Handle YouTube video submission with AI processing
    if request.method == "POST":
        print("DEBUG: education_home POST reached")
        youtube_url = request.POST.get("youtube_url", "").strip()
        title = request.POST.get("video_title", "").strip()
        description = request.POST.get("video_description", "").strip()

        print(f"DEBUG: raw POST values title={repr(title)}, url={repr(youtube_url)}")

        if youtube_url and title:
            print(f"DEBUG: got title and url {title} {youtube_url}")
            try:
                # Extract video ID from URL
                match = re.search(
                    r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&\n?#]+)',
                    youtube_url
                )
                if not match:
                    messages.error(request, "Invalid YouTube URL format.")
                    return redirect("education")

                youtube_id = match.group(1)
                print(f"DEBUG: extracted youtube_id={youtube_id}")

                # Step 1: Get transcript
                print("DEBUG: calling get_youtube_transcript")
                transcript = get_youtube_transcript(youtube_id)
                print(f"DEBUG: transcript present? {bool(transcript)}")

                # Step 2: Generate summary and educational verification
                print("DEBUG: calling generate_ai_summary_and_verify")
                summary, is_verified = generate_ai_summary_and_verify(
                    youtube_id, title, transcript
                )

                # Step 3: Create video record
                video = EducationalVideo.objects.create(
                    title=title,
                    youtube_url=youtube_url,
                    youtube_id=youtube_id,
                    description=description,
                    ai_summary=summary or "",
                    is_verified=is_verified,
                )
                print(f"DEBUG: created video record with id={video.id}")

                # Step 4: Generate quiz questions (only if transcript exists)
                if transcript:
                    print("DEBUG: calling generate_quiz_from_transcript")
                    quiz_questions = generate_quiz_from_transcript(
                        youtube_id, transcript, title
                    )
                    print(f"DEBUG: quiz_questions returned: {len(quiz_questions)} questions")

                    for q_data in quiz_questions:
                        try:
                            VideoQuizQuestion.objects.create(
                                video=video,
                                question=q_data.get("question", ""),
                                option_a=q_data.get("option_a", ""),
                                option_b=q_data.get("option_b", ""),
                                option_c=q_data.get("option_c", ""),
                                option_d=q_data.get("option_d", ""),
                                correct_answer=q_data.get("correct_answer", "A"),
                                explanation=q_data.get("explanation", ""),
                            )
                            print(f"DEBUG: created quiz question for video {video.id}")
                        except Exception as q_err:
                            print(f"DEBUG: error creating quiz question: {q_err}")
                else:
                    print(f"DEBUG: skipping quiz generation, no transcript for {youtube_id}")

                messages.success(
                    request,
                    "Video added successfully with AI-generated content!"
                )
                return redirect("education")

            except Exception as e:
                print(f"DEBUG: exception in POST handler: {e}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error processing video: {str(e)}")
                return redirect("education")
        else:
            messages.error(request, "Please provide both title and YouTube URL.")

    # Fetch all data for display
    featured_lectures = Lecture.objects.filter(section__isnull=True)
    courses = Course.objects.all()
    educational_videos = EducationalVideo.objects.all()

    # Get user's quiz history if authenticated
    user_quiz_history = []
    if user.is_authenticated:
        user_quiz_history = QuizAttempt.objects.filter(user=user)

    context = {
        "is_instructor": is_instructor,
        "featured_lectures": featured_lectures,
        "courses": courses,
        "educational_videos": educational_videos,
        "user_quiz_history": user_quiz_history,
    }
    return render(request, template, context)


@login_required
@require_http_methods(["POST"])
def submit_quiz(request, video_id):
    """
    Handle quiz submission and score calculation.
    Returns JSON with score, total questions, and percentage.
    """
    try:
        video = EducationalVideo.objects.get(id=video_id)
        score = 0
        total_questions = 0

        # Get all questions for this video
        questions = VideoQuizQuestion.objects.filter(video=video)
        total_questions = questions.count()

        if total_questions == 0:
            return JsonResponse(
                {"error": "No questions for this video"},
                status=400
            )

        # Check each answer
        for question in questions:
            user_answer = request.POST.get(
                f"question_{question.id}", ""
            ).upper().strip()
            if user_answer == question.correct_answer.upper():
                score += 1

        percentage = (score / total_questions * 100) if total_questions > 0 else 0

        # Save quiz attempt
        attempt = QuizAttempt.objects.create(
            user=request.user,
            video=video,
            score=score,
            total_questions=total_questions,
            percentage=percentage,
        )

        return JsonResponse(
            {
                "success": True,
                "score": score,
                "total": total_questions,
                "percentage": round(percentage, 2),
                "attempt_id": attempt.id,
            }
        )

    except EducationalVideo.DoesNotExist:
        return JsonResponse(
            {"error": "Video not found"},
            status=404
        )
    except Exception as e:
        print(f"DEBUG: quiz submission error: {e}")
        return JsonResponse(
            {"error": str(e)},
            status=500
        )

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

class VideoDetailView(DetailView):
    model = EducationalVideo
    template_name = "education/video_detail.html"
    context_object_name = "video"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.object
        context["quiz_questions"] = VideoQuizQuestion.objects.filter(video=video)
        if self.request.user.is_authenticated:
            context["quiz_history"] = QuizAttempt.objects.filter(
                user=self.request.user, video=video
            )
        return context