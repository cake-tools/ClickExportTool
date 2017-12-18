# -*- coding: utf-8 -*-

import boto3
import json
import time
import copy
from collections import OrderedDict
import re
import csv
from datetime import datetime, date, timedelta
import requests
from flask import Flask, render_template, url_for, request, redirect, g, jsonify, flash, session, Markup
from run import app
from pymongo import *
from bs4 import BeautifulSoup
from settings import *


client = MongoClient(MONGODB_DATABASE['uri'])
db = client[MONGODB_DATABASE['database_name']]

in_progress = False

def get_country_codes():
    payload = dict(
        api_key=API_KEY,
        )

    endpoint_string = 'http://' + ADMIN_DOMAIN_URL + '/api/1/get.asmx/Currencies'
    soup = requests.post(endpoint_string,json=payload)
    r = soup.json()

    country_codes = {}

    for x in r["d"]["currencies"]:
        abbreviation = x["currency_abbr"]
        currency_id = str(x["currency_id"])
        country_codes[currency_id] = abbreviation

    return country_codes

country_codes = get_country_codes()

def return_currency_name(country_id, country_codes):
    country_id = str(country_id)
    country_name = ''.join({value for key, value in country_codes.items() if country_id == key})
    return country_name


def receive_message():

    in_progress = True
    client = boto3.client('sqs')
    queue_size_response = client.get_queue_attributes(QueueUrl= SQS_QUEUE['url'],
                                                AttributeNames=['ApproximateNumberOfMessages'])
    queue_size = queue_size_response["Attributes"]["ApproximateNumberOfMessages"]
    if queue_size != "0":
        response = OrderedDict(client.receive_message(QueueUrl = SQS_QUEUE['url'],
                                            AttributeNames=['Body'],
                                            MaxNumberOfMessages=1))
        return response
    elif queue_size == "0":
        response = "No Messages in Queue"
        return response

def delete_message(receipt_handle):
    client = boto3.client('sqs')
    response = client.delete_message(QueueUrl= SQS_QUEUE['url'],
                                     ReceiptHandle=receipt_handle)
    return response


def date_convert_for_csv(date):
    extract_integers = re.findall('\d+', date)
    date_string = ''.join(extract_integers)
    if len(date_string) > 10:
        date_string = date_string[:10] + '.' + date_string[10:]
        date_result = datetime.utcfromtimestamp(float(date_string)).strftime("%d-%m-%YT%H:%M:%S.%f")
        return date_result
    else:
        timestamp_parsed = datetime.utcfromtimestamp(int(date_string)) + '.000000'
        date_result = timestamp_parsed.strftime("%d-%m-%YT%H:%M:%S.%f")
        return date_result

def s3_job(filename):
# expire 86400 seconds is 24 hours
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file('temp.csv', S3_BUCKET['name'], '%s.csv' % filename)

    client = boto3.client('s3')
    url = client.generate_presigned_url('get_object',
                                        Params={'Bucket': S3_BUCKET['name'],'Key': '%s.csv' % filename},
                                        ExpiresIn=86400)
    return url


def execute_call(response):

    body = (response["Messages"][0]["Body"]).replace("'", "\"")
    load_body = json.loads(body)

    start_date = load_body['start_date']
    end_date = load_body['end_date']
    job_id = load_body['job_id']
    created_date = load_body['created_date']
    receipt_handle = response["Messages"][0]["ReceiptHandle"]
    delete_message(receipt_handle)

    start_datetime = datetime.strptime(start_date, "%m/%d/%y")
    end_datetime = datetime.strptime(end_date, "%m/%d/%y")
    day_delta = end_datetime - start_datetime

    collection_name = db[MONGODB_DATABASE['collection_name']]
    collection_name.update_one({"created_date": created_date}, {"$set": {"status": "In Progress"}})

    try:
        for i in xrange(day_delta.days + 1):

            for i in xrange(24):
                with open('temp.csv', 'wb') as text_file:
                    writer = csv.writer(text_file)
                    header = 'Click ID', 'Visitor ID', 'Tracking ID', 'Request ID', 'UDID', 'Click Date', \
                            'Affiliate ID', 'Affiliate Name', 'Advertiser ID', 'Advertiser Name', 'Offer ID', \
                            'Offer Name', 'Campaign ID', 'Creative ID', 'Creative Name', 'Sub ID 1', 'Sub ID 2', \
                            'Sub ID 3', 'Sub ID 4', 'Sub ID 5', 'IP Address', 'User Agent', 'Referrer', \
                            'Request URL', 'Redirect URl', 'Country Code', 'Region Code', 'Language', 'ISP', \
                            'Device', 'Operating System', 'OS Major', 'OS Minor', 'Browser', 'Browser Major', \
                            'Browser Minor', 'Disposition', 'Paid Action', 'Currency', 'Amount Paid', \
                            'Duplicate', 'Duplicate Clicks', 'Total Clicks',
                    writer.writerow(header)

                    for i in xrange(60):
                        end_time = start_datetime + timedelta(minutes=1)
                        print start_datetime, end_time

                        endpoint_string = 'http://' + ADMIN_DOMAIN_URL + '/api/11/reports.asmx/Clicks'
                        payload = dict(
                            api_key=API_KEY,
                            start_date=str(start_datetime),
                            end_date=str(end_time),
                            affiliate_id=0,
                            advertiser_id=0,
                            offer_id=0,
                            campaign_id=0,
                            creative_id=0,
                            price_format_id=0,
                            include_duplicates='False',
                            include_tests='False',
                            start_at_row=0,
                            row_limit=0)

                        soup = requests.post(endpoint_string,json=payload, stream=True)
                        print 'PROCESSING API RESPONSE'
                        #soup_text = soup.text
                        response = json.loads(soup.text)
			#print response

                        for c in response['d']['clicks']:
                            click_id = c['click_id']
                            visitor_id = c['visitor_id']
                            tracking_id = c['tracking_id']
                            request_id = c['request_session_id']
                            udid = ''
                            if not c['udid'] is None:
                                udid = c['udid'].encode('utf-8', 'ignore')
                            click_date = date_convert_for_csv(c['click_date'])
                            affiliate_id = c['source_affiliate']['source_affiliate_id']
                            affiliate_name = c['source_affiliate']['source_affiliate_name'].encode('utf-8', 'ignore')
                            advertiser_id = c['brand_advertiser']['brand_advertiser_id']
                            advertiser_name = c['brand_advertiser']['brand_advertiser_name'].encode('utf-8', 'ignore')
                            offer_id = c['site_offer']['site_offer_id']
                            offer_name = c['site_offer']['site_offer_name'].encode('utf-8', 'ignore')
                            campaign_id = c['campaign']['campaign_id']
                            creative_id = c['creative']['creative_id']
                            creative_name = c['creative']['creative_name'].encode('utf-8', 'ignore')
                            sub_id_1 = c['sub_id_1'].encode('utf-8', 'ignore')
                            sub_id_2 = c['sub_id_2'].encode('utf-8', 'ignore')
                            sub_id_3 = c['sub_id_3'].encode('utf-8', 'ignore')
                            sub_id_4 = c['sub_id_4'].encode('utf-8', 'ignore')
                            sub_id_5 = c['sub_id_5'].encode('utf-8', 'ignore')
                            ip_address = c['ip_address']

                            user_agent  = ''
                            if not c['user_agent'] is None:
                                user_agent = c['user_agent'].encode('utf-8', 'ignore')
                            referrer_url = ''
                            if not c['referrer_url'] is None:
                                referrer_url = c['referrer_url'].encode('utf-8', 'ignore')
                            request_url = ''
                            if not c['request_url'] is None:
                                request_url = c['request_url'].encode('utf-8', 'ignore')
                            redirect_url = ''
                            if not c['redirect_url'] is None:
                                redirect_url = c['redirect_url'].encode('utf-8', 'ignore')
                            country_code = ''
                            if not c['country'] is None:
                                country_code = c['country']['country_code'].encode('utf-8', 'ignore')
                            region = ''
                            if not c['region'] is None:
                                region = c['region']['region_name'].encode('utf-8', 'ignore')
                            language = ''
                            if not c['language'] is None:
                                language = c['language']['language_name'].encode('utf-8', 'ignore')
                            isp = ''
                            if not c['isp'] is None:
                                isp = c['isp']['isp_name'].encode('utf-8', 'ignore')
                            device = ''
                            if not c['device'] is None:
                                device = c['device']['device_name'].encode('utf-8', 'ignore')
                            operating_system = ''
                            os_major = ''
                            os_minor = ''
                            if not c['operating_system'] is None:
                                operating_system = c['operating_system']['operating_system_name'].encode('utf-8', 'ignore')
                                os_major = c['operating_system']['operating_system_version']['version_name']
                                os_minor = c['operating_system']['operating_system_version_minor']['version_name']
                            browser = ''
                            browser_major = ''
                            browser_minor = ''
                            if not c['browser'] is None:
                                browser = c['browser']['browser_name'].encode('utf-8', 'ignore')
                                browser_major = c['browser']['browser_version']['version_name']
                                browser_minor = c['browser']['browser_version_minor']['version_name']
                            disposition = c['disposition']
                            paid_action = ''
                            if not c['paid_action'] is None:
                                paid_action = c['paid_action']
                            currency = ''
                            amount_paid = ''
                            if not c['paid'] is None:
                                currency = return_currency_name(c['paid']['currency_id'], country_codes)
                                amount_paid = c['paid']['amount']
                            duplicate = c['duplicate']
                            duplicate_clicks = c['duplicate_clicks']
                            total_clicks = c['total_clicks']

                            record = click_id, visitor_id, tracking_id, request_id, udid, \
                                    click_date, affiliate_id, affiliate_name, advertiser_id, \
                                    advertiser_name, offer_id, offer_name, campaign_id, \
                                    creative_id, creative_name, sub_id_1, sub_id_2, sub_id_3, \
                                    sub_id_4, sub_id_5, ip_address, user_agent, referrer_url, \
                                    request_url, redirect_url, country_code, region, language, \
                                    isp, device, operating_system, os_major, os_minor, browser, \
                                    browser_major, browser_minor, disposition, paid_action, \
                                    currency, amount_paid, duplicate, duplicate_clicks, total_clicks,

                            writer.writerow(record)

                        print 'INTERVAL COMPLETE'
                        start_datetime += timedelta(minutes=1)

                    file_link = s3_job('ClickReport_{}{}{}_{}{}_{}{}'.format((start_datetime - timedelta(hours=1)).strftime('%d'),
                                                                        (start_datetime - timedelta(hours=1)).strftime('%m'),
                                                                        (start_datetime - timedelta(hours=1)).year,
                                                                        (start_datetime - timedelta(hours=1)).strftime('%H'),
                                                                        (start_datetime - timedelta(hours=1)).strftime('%M'),
                                                                        start_datetime.strftime('%H'),
                                                                        start_datetime.strftime('%M')))
                    print 'File link:', file_link

        print 'QUEUED REPORT CREATED SUCCESSFULLY'
        print 'CHECKING FOR ADDITIONAL QUEUED EXPORTS'

        collection_name = db[MONGODB_DATABASE['collection_name']]
        collection_name.update_one({"created_date": created_date}, {"$set": {"status": "Success"}})
        in_progress = False

    except (KeyboardInterrupt, Exception, KeyError):
        print "Key Error occurred"
        in_progress = False

start_time = time.time()

if __name__ == "__main__":
    while True:
        if in_progress == True:
            time.sleep(60.0 - ((time.time() - start_time) % 60.0))
        else:
            response = receive_message()
            if response == "No Messages in Queue":
                print response
                time.sleep(60.0 - ((time.time() - start_time) % 60.0))
            else:
                execute_call(response)
                time.sleep(60.0 - ((time.time() - start_time) % 60.0))
