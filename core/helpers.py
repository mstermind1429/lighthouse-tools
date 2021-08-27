import logging
from json import JSONDecodeError
import random
import requests


import urllib.parse as urlparse

from django.core.mail import EmailMessage
from django.core.files.storage import FileSystemStorage
from django.conf import settings

from alighthouse.models import *

logger = logging.getLogger('django')

numeric_aspects = {"first-contentful-paint": "first_cp", "largest-contentful-paint": "largest_cp",
                   "first-meaningful-paint": "first_mp", "speed-index": "speed_index",
                   "estimated-input-latency": "estimated_il", "total-blocking-time": "total_blocking_time",
                   "max-potential-fid": "max_potential_fid", "cumulative-layout-shift": "cumulative_ls",
                   "server-response-time": "server_response_time", "first-cpu-idle": "first_cpu_idle",
                   "interactive": "interactive", "redirects": "redirects",
                   "mainthread-work-breakdown": "mainthread_work_breakdown", "bootup-time": "bootup_time",
                   "uses-rel-preload": "uses_rel_preload", "network-rtt": "network_rtt",
                   "network-server-latency": "network_sl", "uses-long-cache-ttl": "long_cache_ttl"}

score_aspects = {
    "largest-contentful-paint": "lcp_score",
    "max-potential-fid": "fid_score",
    "cumulative-layout-shift": "cls_score"
}

items = {"bootup-time": LighthouseReportBootupItems, "diagnostics": LighthouseReportDiagnosticsItems,
         "network-requests": LighthouseReportNetworkReqItems, "network-rtt": LighthouseReportNetworkRttItems,
         "network-server-latency": LighthouseReportNetworkSLItems, "long-tasks": LighthouseReportLongTaskItem,
         "offscreen-images": LighthouseReportOffscreenImagesItem, "unminified-javascript": LighthouseReportUnminifiedJS,
         "unminified-css": LighthouseReportUnminifiedCSS, "unused-css-rules": LighthouseReportUnusedCSSRule}

FILE_PATH = settings.REPORT_PATH + '/urls_lighthouse.xlsx'


def average(lst):
    return round(sum(lst) / len(lst), 2)


def generate_random_number():
    return random.randint(1000000, 9999999)


def generate_directories(url):
    return urlparse.urlparse(url).path.split("/")[1:]


def get_domain(url):
    return urlparse.urlparse(url).netloc


def get_subdomain(url):
    return '.'.join(urlparse.urlparse(url).netloc.split('.')[:-2])


def save_csv_file(csv_file, filename):
    fs = FileSystemStorage()
    file_name = fs.save(filename, csv_file)
    uploaded_file_url = fs.url(file_name)
    return uploaded_file_url


def log_to_telegram_bot(message):
    api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_API}/sendMessage?" \
              f"chat_id=48355225&text={message}"
    requests.get(url=api_url)


def send_mail(subject, message, file_attachment=None):
    from_email = settings.EMAIL_HOST_USER
    mail = EmailMessage(subject, message, from_email,
                        ['abror.ruzibayev@gmail.com', 'k.kleinschmidt@searchmetrics.com'])
    if file_attachment:
        mail.attach_file(file_attachment)
    mail.send(fail_silently=False)


def get_page_google_analysis(url):
    api_url = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'

    try:
        response = requests.get(
            api_url,
            params=
            {
                'url': url,
            }
        ).json()
    except JSONDecodeError:
        return None, None, None

    try:
        audits = response['lighthouseResult']['audits']
        lcp = audits['largest-contentful-paint']['numericValue']
        fid = audits['max-potential-fid']['numericValue']
        cls = audits['cumulative-layout-shift']['numericValue']
    except (KeyError, TypeError, ValueError):
        lcp, fid, cls = None, None, None

    return lcp, fid, cls
