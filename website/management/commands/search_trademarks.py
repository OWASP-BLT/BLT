import requests
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from website.models import Company, Domain
from website.utils import search_uspto_database, send_email_alert

class Command(BaseCommand):
    help = "Search the USPTO database for trademarks and alert companies if their brand name is at risk"

    def handle(self, *args, **options):
        companies = Company.objects.all()
        for company in companies:
            domains = Domain.objects.filter(company=company)
            for domain in domains:
                search_terms = [company.name, domain.name]
                for term in search_terms:
                    results = search_uspto_database(term)
                    if results:
                        send_email_alert(company, results)
