from functools import wraps

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from website.models import Course, Lecture, Section


def instructor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        course = None

        if "course_id" in kwargs:
            course = get_object_or_404(Course, id=kwargs["course_id"])
        elif "lecture_id" in kwargs:
            lecture = get_object_or_404(Lecture, id=kwargs["lecture_id"])
            course = lecture.section.course
        elif "section_id" in kwargs:
            section = get_object_or_404(Section, id=kwargs["section_id"])
            course = section.course

        if not course or request.user != course.instructor.user:
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return _wrapped_view
