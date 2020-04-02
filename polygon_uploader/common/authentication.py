import os
import yaml
from polygon_api import Polygon


def authenticate():
    default_polygon_url = "https://polygon.codeforces.com"

    authentication_file = os.path.join(os.path.expanduser('~'), '.config', 'polygon_uploader', 'auth.yaml')
    api_key = None
    api_secret = None
    polygon_url = None
    if os.path.exists(authentication_file):
        with open(authentication_file, 'r') as fo:
            auth_data = yaml.load(fo, Loader=yaml.BaseLoader)
        polygon_url = auth_data.get('polygon_url', default_polygon_url)
        api_key = auth_data.get('api_key')
        api_secret = auth_data.get('api_secret')

    if not os.path.exists(authentication_file) or not api_key or not api_secret:
        print('WARNING: Authentication data will be stored in plain text in {}'.format(authentication_file))
        api_key = input('API Key: ')
        api_secret = input('API Secret: ')
        polygon_url = default_polygon_url
        os.makedirs(os.path.dirname(authentication_file), exist_ok=True)
        with open(authentication_file, 'w') as fo:
            auth_data = {
                'polygon_url': polygon_url,
                'api_key': api_key,
                'api_secret': api_secret
            }
            yaml.dump(auth_data, fo, default_flow_style=False)
        print('Authentication data is stored in {}'.format(authentication_file))
    polygon_url += '/api'
    return Polygon(polygon_url, api_key, api_secret)
