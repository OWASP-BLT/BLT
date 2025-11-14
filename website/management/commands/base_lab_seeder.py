from typing import ClassVar

from django.core.management.base import BaseCommand, CommandError

from website.models import Labs, TaskContent, Tasks


class LabSeederCommand(BaseCommand):
    lab_name: ClassVar[str | None] = None  # Override in subclass
    tasks_data: ClassVar[list] = []  # Override in subclass

    def handle(self, *args, **kwargs):
        try:
            lab = Labs.objects.get(name=self.lab_name)
        except Labs.DoesNotExist as err:
            raise CommandError(f"{self.lab_name} lab not found. Please run create_initial_labs first.") from err

        for task_data in self.tasks_data:
            task, created = Tasks.objects.update_or_create(
                lab=lab,
                order=task_data["order"],
                defaults={
                    "name": task_data["name"],
                    "description": task_data["description"],
                    "task_type": task_data["task_type"],
                    "is_active": True,
                },
            )

            content_data = self._build_content_data(task_data)
            _, content_created = TaskContent.objects.update_or_create(task=task, defaults=content_data)

            self._log_task_status(task, created, content_created)

        lab.update_total_tasks()
        self.stdout.write(self.style.SUCCESS(f"{self.lab_name} lab setup complete with {lab.total_tasks} tasks"))

    def _build_content_data(self, task_data):
        if task_data["task_type"] == "theory":
            return {
                "theory_content": task_data.get("theory_content", ""),
                "mcq_question": task_data.get("mcq_question", ""),
                "mcq_options": task_data.get("mcq_options", []),
                "correct_answer": task_data.get("correct_answer", ""),
            }
        return {"simulation_config": task_data.get("simulation_config", {})}

    def _log_task_status(self, task, created, content_created):
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created task: "{task.name}"'))
        else:
            self.stdout.write(self.style.WARNING(f'Task "{task.name}" already exists'))

        if content_created:
            self.stdout.write(self.style.SUCCESS(f'Created content for task: "{task.name}"'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Updated content for task: "{task.name}"'))
