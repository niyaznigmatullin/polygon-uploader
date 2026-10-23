import os
import time
import yaml
from polygon_api import Polygon, HTTPRequestFailedException


class RetryingPolygon(Polygon):
    """Sends at most one request per MIN_REQUEST_INTERVAL seconds and retries requests
    rejected by Polygon with HTTP 429 (Too Many Requests) or a transient 5xx"""

    RETRIED_CODES = ('429', '502', '503', '504')
    MIN_REQUEST_INTERVAL = 1.0

    _last_request_time = 0.0

    def _request(self, method_name, args=None):
        delay = 5
        while True:
            wait = self._last_request_time + self.MIN_REQUEST_INTERVAL - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last_request_time = time.monotonic()
            try:
                return super()._request(method_name, args)
            except HTTPRequestFailedException as e:
                code = next((c for c in self.RETRIED_CODES if c in e.comment), None)
                if code is None or delay > 300:
                    raise
                print("%s: HTTP %s, retrying in %d seconds" % (method_name, code, delay))
                time.sleep(delay)
                delay *= 2


def authenticate():
    default_polygon_url = "https://polygon.codeforces.com"

    if os.getenv('POLYGON_API_KEY') and os.getenv('POLYGON_API_SECRET'):
        polygon_url = os.getenv('POLYGON_URL', default_polygon_url)
        return RetryingPolygon(polygon_url + '/api', os.getenv('POLYGON_API_KEY'), os.getenv('POLYGON_API_SECRET'))

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
    return RetryingPolygon(polygon_url, api_key, api_secret)
