import unittest
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.core.mail import send_mail
from website.models import Company, Domain
from website.utils import search_uspto_database, send_email_alert

class SearchTrademarksCommandTest(unittest.TestCase):

    @patch('website.utils.search_uspto_database')
    @patch('website.utils.send_email_alert')
    def test_handle(self, mock_send_email_alert, mock_search_uspto_database):
        # Setup mock data
        company = Company(name="TestCompany", email="test@example.com")
        domain = Domain(name="testdomain", company=company)
        company.save()
        domain.save()

        mock_search_uspto_database.return_value = [{"trademark": "TestTrademark"}]

        # Call the management command
        call_command('search_trademarks')

        # Assertions
        mock_search_uspto_database.assert_called_with("TestCompany")
        mock_search_uspto_database.assert_called_with("testdomain")
        mock_send_email_alert.assert_called_with(company, [{"trademark": "TestTrademark"}])

class UtilsTest(unittest.TestCase):

    @patch('requests.get')
    def test_search_uspto_database(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": "test"}
        mock_get.return_value = mock_response

        result = search_uspto_database("test")
        self.assertEqual(result, {"results": "test"})

    @patch('django.core.mail.send_mail')
    def test_send_email_alert(self, mock_send_mail):
        company = Company(name="TestCompany", email="test@example.com")
        results = {"results": "test"}

        send_email_alert(company, results)
        mock_send_mail.assert_called_with(
            "Trademark Alert for TestCompany",
            "Potential trademark matches found:\n\n{'results': 'test'}",
            "from@example.com",
            ["test@example.com"]
        )
