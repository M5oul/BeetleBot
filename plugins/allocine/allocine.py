from datetime import date, timedelta
import hashlib, base64
import json
import urllib.request, urllib.error, urllib.parse, urllib.request, urllib.parse, urllib.error
from collections import OrderedDict


class Allocine(object):
    """An interface to the Allocine API"""
    def __init__(self, partner_key=None, secret_key=None):
        """Init values"""
        self._api_url = 'http://api.allocine.fr/rest/v3'
        self._partner_key  = 'aXBob25lLXYy'
        self._secret_key = secret_key
        self._user_agent = 'AlloCine/2.9.5 CFNetwork/548.1.4 Darwin/11.0.0'

    def configure(self, partner_key=None, secret_key=None):
        """Set the keys"""
        self._partner_key = 'aXBob25lLXYy'
        self._secret_key = secret_key

    def _do_request(self, method=None, params=None):
        """Generate and send the request"""
        # build the URL
        query_url = self._api_url+'/'+method;

        # new algo to build the query
        today = date.today()
        sed = today.strftime('%Y%m%d')
        to_hash = (self._secret_key + urllib.parse.urlencode(params) + '&sed=' + sed).encode("utf8")
        sha1 = hashlib.sha1(to_hash).digest()
        b64 = base64.b64encode(sha1)
        sig = urllib.parse.quote(b64)
        #query_url += '?'+urllib.urlencode(params)+'&sed='+sed+'&sig='+sig
        query_url += '?'+urllib.parse.urlencode(params, True)

        # do the request
        req = urllib.request.Request(query_url)
        req.add_header('User-agent', self._user_agent)


        str_response = urllib.request.urlopen(req, timeout = 10).read().decode()
        response = json.loads(str_response)

        return response;

    def show_time(self, time):
        params = {}
        params['format'] = 'json'
        params['partner'] = self._partner_key
        params['zip'] = 29200

        if time == "today":
            today = date.today()
            params['date'] = today.strftime("%Y-%m-%d")
        elif time is None:
            # Find next sunday.
            today = date.today()
            sunday = today + timedelta((6-today.weekday()) % 7)
            params['date'] = sunday.strftime("%Y-%m-%d")
        else:
            params['date'] = time
        response = self._do_request('showtimelist', params);

        return response, params['date']


def get_movies(time):
    api = Allocine()
    api.configure('100043982026','29d185d98c984a359e6e6f26a0474269')

    movies = OrderedDict()
    response, chosen_time = api.show_time(time)
    theaters = response['feed']['theaterShowtimes']
    for theater in theaters:
        if theater['place']['theater']['name'] == "L'Image":
            continue
        theater_name = theater['place']['theater']['name']
        movies[theater_name] = {}

        for movie in theater['movieShowtimes']:
            vo = movie['version']['original'] != 'false'

            m = movies[theater_name][movie['onShow']['movie']['title'] + ' ' * vo] = {}
            m['vo'] = vo
            m['times'] = []
            for d in movie['scr']:
                for t in d.get('t', []):
                    m['times'].append(t['$'])
    return movies, chosen_time

