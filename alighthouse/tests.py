import logging

from django.test import TestCase
from django.conf import settings

from alighthouse.core import lighthouse_report, run_domain_lighthouse

logger = logging.getLogger('django')


class LighthouseTests(TestCase):
    def setUp(self):
        return

    # def test_lighthouse_report_func(self):
    #     data = lighthouse_report('https://zappos.com')
    #     self.assertIsInstance(data, dict)
    #     self.assertNotEqual(data['data'], [])
    #     print(data)

    def test_domain_lighthouse(self):
        domain_lighthouse = run_domain_lighthouse(
            key=settings.SEARCH_METRICS_KEY,
            secret=settings.SEARCH_METRICS_SECRET,
            amount=250,
            country_code='us',
            domain='target.com'
        )

        self.assertEquals(domain_lighthouse, True)
