import csv
import logging
from json import JSONDecodeError

from django.conf import settings
from django.db import IntegrityError

from background_task import background
from lighthouse import LighthouseRunner
import pandas as pd
from urllib.parse import urlparse

from core.helpers import (generate_random_number, send_mail, items, score_aspects, numeric_aspects,
                          get_page_google_analysis)
from core.searchmetrics import SearchmetricsAPI
from .models import *

logger = logging.getLogger('django')


# TODO: Writing to file replace with appropriate method
# TODO: KeyError: largestContentfulPaint
def lighthouse_report(
        url: str
) -> dict:
    report_types = ['mobile', 'desktop']
    domain = urlparse(url).netloc
    report_name = f'lighthouse_{domain}_{generate_random_number()}_'
    report_path = settings.REPORT_URL + report_name

    serializer = {
        'desktop_report_path': report_path + 'desktop.json',
        'mobile_report_path': report_path + 'mobile.json',
        'data': []
    }

    for report_type in report_types:
        content_type, largest_cp_element = None, None
        report_path = f'{settings.REPORT_PATH}/{report_name}{report_type}.json'

        report = LighthouseRunner(
            url=url,
            form_factor=report_type,
            quiet=False,
            report_path=report_path
        ).report

        try:
            snippet = report.get_audits()['largest-contentful-paint-element']['details']['items'][0]['node']['snippet']
            largest_cp_element = snippet.split("src=\"")[1].split("\"")[0]
            content_type = 'image'
        except (KeyError, ValueError, IndexError, TypeError) as e:
            logger.info(f"No image found for the LCP. Error: {e}")

        if not content_type:
            try:
                detail_items = report.get_audits()['largest-contentful-paint-element']['details']['items']
                node = detail_items[0]['node']['nodeLabel']
                largest_cp_element = node
                content_type = 'node'
            except (KeyError, ValueError, IndexError, TypeError) as e:
                logger.info(f"No node found for the LCP. Error: {e}")

        data = {
            'paint_score': report.get_audits()['largestContentfulPaint']['numericValue'],
            'cumulative_ls': report.get_audits()['cumulativeLayoutShift']['numericValue'],
            'max_potential_fid': report.get_audits()['maxPotentialFid']['numericValue'],
            'largest_cp_element': largest_cp_element,
            'content_type': content_type,
            'audits': report.audits
         }

        file_name = f'{report_name}{report_type}.csv'
        with open(f'{settings.REPORT_PATH}/{file_name}', 'w+', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([domain, report_type])

            for key in data:
                if key is not 'audits':
                    writer.writerow([key, data[key]])
                else:
                    for audit in data['audits']['performance']:
                        for aspect in audit:
                            writer.writerow([aspect[0], aspect[1], aspect[2]])

        data['csv'] = file_name
        serializer['data'].append(data)

    return serializer


@background(schedule=1)
def run_domain_lighthouse(
        key: str,
        secret: str,
        amount: int,
        country_code: str,
        domain: str,
        uploaded_file_url: str = None
):
    api = SearchmetricsAPI(key, secret)

    if not uploaded_file_url:
        keyword_info = {}
        keywords = []
        offset = 0
        for _ in range(amount // 250):
            status, response = api.get_rankings_domain(
                domain=domain,
                country_code=country_code,
                offset=offset
            )

            for element in response:
                keywords.append(element['keyword'])
                keyword_info[element['keyword']] = element

            offset += 250

        ranking = []
        keywords_list, position, urls = [], [], []
        for index, keyword in enumerate(keywords):
            status, ranking_info = api.get_list_rankings_keyword(
                keyword=keyword,
                country_code=country_code
            )

            if not status:
                continue

            if len(ranking_info) == 0:
                ranking.append(keyword)

            for info in ranking_info:
                keywords_list.append(keyword)
                position.append(info['position'])
                urls.append(info['url'])

        df = pd.DataFrame(
            {
                'Keyword': keywords_list,
                'URL': urls,
                'Position': position,
            }
        )
    else:
        df = pd.read_excel(f'/{uploaded_file_url}')
        keywords_list = df['Keyword']
        amount = len(keywords_list)

    if len(keywords_list) == 0:
        send_mail('Domain Lighthouse', f'No data received for domain {domain}. Values set:\n'
                                       f'Country code: {country_code}\nAmount: {amount}')
        return

    result = run_lighthouse_report(df, domain, amount)
    return result


def run_lighthouse_report(df, domain, amount):
    failed, completed, already_exists = [], [], []
    for url, keyword, position in zip(df["URL"], df["Keyword"], df["Position"]):
        url = f"https://{url}"
        report_types = ['mobile']

        for report_type in report_types:
            try:
                report = LighthouseRunner(url, form_factor=report_type, quiet=False).report
            except (TypeError, RuntimeError, JSONDecodeError) as err:
                logger.info(err)
                failed.append(url)
                continue

            audits = report.get_audits()
            content_type, node = None, None
            try:
                node = audits['largest-contentful-paint-element']['details']['items'][0]['node']['snippet']
                node.replace('{', '').replace('}', '')
                content_type = 'image'
            except (IndexError, KeyError, TypeError) as err:
                logger.info(f'Error occurred while getting LCP: {err}')

            try:
                node = audits['largest-contentful-paint-element']['details']['items'][0]['node']['nodeLabel']
                node.replace('{', '').replace('}', '')
                content_type = 'node'
            except (IndexError, KeyError, TypeError) as err:
                logger.info(f'Error occurred while getting LCP: {err}')

            if content_type is None:
                content_type = 'error'

            lighthouse_report = {}
            for key in numeric_aspects:
                try:
                    lighthouse_report[numeric_aspects[key]] = round(audits[key]['numericValue'], 3)
                except KeyError:
                    failed.append(url)
                    continue

            for key in score_aspects:
                try:
                    lighthouse_report[score_aspects[key]] = audits[key]['score']
                except KeyError:
                    continue

            lighthouse_report['domain'] = domain
            lighthouse_report['url'] = url
            lighthouse_report['keyword'] = keyword
            lighthouse_report['type'] = report_type
            lighthouse_report['position'] = position
            lighthouse_report['content_type'] = content_type
            lighthouse_report['largest_cp_element'] = node

            lcp, fid, cls = get_page_google_analysis(url)

            lighthouse_report['lcp_field'] = lcp
            lighthouse_report['fid_field'] = fid
            lighthouse_report['cls_field'] = cls

            try:
                lighthouse_report = LighthouseReport.objects.create(**lighthouse_report)
            except IntegrityError:
                lighthouse_report = LighthouseReport.objects.filter(domain='taz.de', url=url, keyword=keyword)

                if not lighthouse_report:
                    failed.append(url)
                else:
                    already_exists.append(url)
                continue

            completed.append(url)

            for key in ["screenshot-thumbnails", "final-screenshot"]:
                try:
                    for item in audits[key]['details']['items']:
                        lighthouse_item = {}
                        for aspect in item:
                            if type(item[aspect]) == str:
                                if '{' in item[aspect] or '}' in item[aspect]:
                                    continue
                            if aspect == 'data':
                                lighthouse_item["content_type"] = item[aspect].split(";")[0]
                                lighthouse_item["data"] = item[aspect].split(";")[1]
                                continue
                            lighthouse_item[aspect] = item[aspect]

                        lighthouse_item["report"] = lighthouse_report

                        LighthouseReportItem.objects.create(**lighthouse_item)
                except Exception as err:
                    logger.info(err)
                    continue

            for key in items:
                try:
                    fields = [field.name for field in items[key]._meta.fields]

                    for item in audits[key]['details']['items']:
                        lighthouse_item = {}
                        for aspect in item:
                            if aspect in fields:
                                if type(item[aspect]) == str:
                                    if '{' in item[aspect] or '}' in item[aspect]:
                                        continue
                                lighthouse_item[aspect] = round(item[aspect], 2) if type(item[aspect]) == float \
                                    else item[aspect]
                        lighthouse_item["report"] = lighthouse_report

                        items[key].objects.create(**lighthouse_item)
                except (KeyError, ValueError, TypeError) as err:
                    logger.info(err)
                    continue

            try:
                for item in audits["layout-shift-elements"]['details']['items']:
                    node = item["node"]
                    lighthouse_item = {}

                    fields = [field.name for field in LighthouseReport._meta.fields]

                    for aspect in node:
                        if aspect != "boundingRect" and aspect in fields:
                            if type(node[aspect]) == str:
                                if '{' in node[aspect] or '}' in node[aspect]:
                                    continue
                            lighthouse_item[aspect] = round(node[aspect], 2) if type(node[aspect]) == float \
                                else node[aspect]
                    lighthouse_item["report"] = lighthouse_report

                    LighthouseReportLayoutElementsItem.objects.create(**lighthouse_item)
            except (KeyError, ValueError, TypeError) as err:
                logger.info(err)
                continue

    file_name = f'lighthouse_report_{domain}.xlsx'
    output = f'{settings.REPORT_PATH}/{file_name}'
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    keywords = df['Keyword']
    df = pd.DataFrame(
        {
            'Requested': [amount],
            'Requested from API': [len(keywords)],
        }
    )
    df.to_excel(writer, sheet_name='requested', index=False)

    df = pd.DataFrame(
        {
            'Total URLs': [len(list(set(keywords))) * 10],
            'Failed': [len(failed)],
            'Completed': [len(completed)]
        }
    )
    df.to_excel(writer, sheet_name='results', index=False)

    failed = pd.DataFrame({'Keyword': failed})
    failed.to_excel(writer, sheet_name='failed', index=False)
    completed = pd.DataFrame({'Keyword': completed})
    completed.to_excel(writer, sheet_name='completed', index=False)
    writer.save()

    send_mail('Lighthouse Run', f'Lighthouse Run for domain {domain} is completed. ', output)

    return True
