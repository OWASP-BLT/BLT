import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Monthly Email'

    def handle(self, *args, **options):
        today = datetime.date.today()
        # upload users to mailchimp
        # send from mailchimp

        # if today.day == 1:
        #     first = today.replace(day=1)
        #     lastMonth = first - datetime.timedelta(days=1)

        #     subject = 'Bugheist ' + lastMonth.strftime("%B") + ' summary'
        #     msg_plain = msg_html = render_to_string('email/bug_summary.txt', {
        #         'month': lastMonth.strftime("%B"),
        #         'leaderboard': User.objects.filter(points__created__month=lastMonth.strftime("%m")).annotate(
        #             total_score=Sum('points__score')).order_by('-total_score')[:5],
        #         'responsive': Domain.objects.filter(email_event__in=['open', 'delivered', 'click']).order_by(
        #             '-modified')[:3],
        #         'closed_issues': Domain.objects.filter(issue__status="closed").annotate(count=Count('issue')).order_by(
        #             '-count')[:3],
        #         'open_issues': Domain.objects.exclude(issue__status="closed").annotate(count=Count('issue')).order_by(
        #             '-count')[:3],
        #         'most_viewed': Issue.objects.filter(views__gte=0).order_by('-views')[:3],
        #     })

        #     result_list = sorted(
        #         chain(User.objects.all(), Domain.objects.all()),
        #         key=attrgetter('email'))

        #     unique_results = [rows.next() for (key, rows) in groupby(result_list, key=lambda obj: obj.email)]

        #     for user in unique_results:
        #         if user.email:
        #             send_mail(
        #                 subject,
        #                 msg_plain,
        #                 'Bugheist <support@bugheist.com>',
        #                 [user.email],
        #                 html_message=msg_html,
        #             )
