import requests
from bs4 import BeautifulSoup
import collections
import validation


def get_api_key(admin_domain, username, password):

    endpoint_string = 'http://' + admin_domain + '/api/1/get.asmx/GetAPIKey'
    payload = dict(username=username, password=password)

    valid_call, soup = validation.soup_validation(endpoint_string,payload)

    if valid_call == True:
        api_key = soup.find('string').get_text()
    else:
        api_key = ''

    return api_key
