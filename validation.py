import requests
from bs4 import BeautifulSoup


def soup_validation(endpoint, payload):
    try:
        soup = ''  # if the below request fails completely, we still need to return a soup

        r = requests.get(endpoint, params=payload)
        soup = BeautifulSoup(r.text)

        if 'GetAPIKey' in endpoint:
            if not soup.find('string').get_text():
                valid_call = False
                return valid_call, soup

            else:
                valid_call = True
                return valid_call, soup

        elif 'Advertisers' in endpoint:
            adv_count = soup.find_all('advertiser')
            if len(adv_count) > 0:
                valid_call = True
                return valid_call, soup

            else:
                valid_call = False
                return valid_call, soup
        else:
            if soup.find('success').get_text() == 'true':
                valid_call = True
                return valid_call, soup

            else:
                valid_call = False
                return valid_call, soup

    except Exception as ex:
        valid_call = False
        template = "An exception of type {0} occured. Arguments:\n{1!r}"
        message = template.format(type(ex).__name__, ex.args)
        print(message)
        return valid_call, soup