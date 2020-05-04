import os
import json
import requests
import hashlib
import logging

from datetime import date
from datetime import datetime
from datetime import timedelta

class YoutubeAPIException(Exception):
    def __init__(self, response):
        super().__init__(response['error']['message'])


class RequestCache:
    DUMP_FILE_NAME = ".request_cache.json"
    def __init__(self, dump_dir=".", expires=timedelta(days=1.0), logger=None):
        self._dump_dir = dump_dir
        self._expires = expires
        self._logger = logger if logger else logging
        self._cache_file = "%s/%s" % (os.path.abspath(dump_dir),
                self.DUMP_FILE_NAME)
        self._load()

    def _load(self):
        cache= {}
        if os.path.isfile(self._cache_file):
            with open(self._cache_file, 'r') as f:
                cached_requests = json.load(f)
                for request_hash, (time_str, response) in cached_requests.items():
                    time = datetime.fromisoformat(time_str)
                    if datetime.now() - time < self._expires:
                        cache[request_hash] = (time_str, response)

        self._cache = cache

    #def _save(self):
    #    with open(self._cache_file, 'w') as f:
    #        json.dump(self._cache, f)

    #def _request_hash(self, method, params):
    #    params= { str(key): str(value) for key, value in params.items()}
    #    to_hash = (method+''.join(params.values())).encode("utf-8")
    #    request_hash = hashlib.sha224(to_hash).hexdigest()
    #    return request_hash

    #def get_request(self, method, params):
    #    request_hash = self._request_hash(method, params)
    #    if request_hash in self._cache.keys():
    #        time_str, response = self._cache[request_hash]
    #        time = datetime.fromisoformat(time_str)
    #        if datetime.now() - time < self._expires:
    #            self._logger.info("Loading request ")
    #            return response
    #    return None

    #def save_request(self, method, params, response_json):
    #    self._logger.info("Saving request ")
    #    request_hash = self._request_hash(method, params)
    #    self._cache[request_hash] = (str(datetime.now()), response_json)
    #    self._save()


    def cache(self, func):
        def do_caching(method="", params={}):
            # generate hash of the request, used as identifier
            params= { str(key): str(value) for key, value in params.items()}
            to_hash = (method+''.join(params.values())).encode("utf-8")
            request_hash = hashlib.sha224(to_hash).hexdigest()
            # ? is request cached
            #request_hash = self._request_hash(method, params)
            if request_hash in self._cache.keys():
                time_str, response_json = self._cache[request_hash]
                # only use not expired requests
                time = datetime.fromisoformat(time_str)
                if datetime.now() - time < self._expires:
                    self._logger.info("Loading request ")
                    return response_json

            #response_json = self.get_request(method, params)
            #if not response_json:
            # response not cached!
            response_json = func(method, params)
            # cache it
            self._logger.info("Saving request ")
            self._cache[request_hash] = (str(datetime.now()), response_json)
            #self.save_request(method, params, response_json)
            # write to file, in case of sudden termination of the script
            # __del__ not relyable!
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache, f)
            return response_json
        return do_caching

class YoutubeAPI:
    BASE_URL = "https://www.googleapis.com/youtube/v3/"

    def __init__(self, developer_key, dump_dir=None, logger=None, caching=True,
            caching_delay=timedelta(days=1.0)):
        self._developer_key = developer_key
        self._dump_dir = dump_dir if dump_dir else "request_json_dump/"
        self._logger = logger if logger else logging
        try:
            os.mkdir(self._dump_dir)
        except FileExistsError:
            pass
        if caching:
            cache = RequestCache(expires=caching_delay)
            self._request = cache.cache(self._request)

    def _check_for_errors(self, response):
        if 'error' in response.keys():
            raise YoutubeAPIException(response)

    def _request(self, method="search", params=dict()):
        # some search params maybe int ...
        params= { str(key): str(value) for key, value in params.items()}
        request_params ={
                **params,
                'key' : self._developer_key,
        }
        # disable proxy for faster response
        proxies = {
            "http": None,
            "https": None,
        }
        params_hash = hashlib.sha224(''.join(params.values()).encode("utf-8")
                ).hexdigest()
        dump_file = "%s/%s_%s_%s.json" % (self._dump_dir, method, params_hash,
                date.today())

        #response_dict = self._cache.get_request(method, params)
        #if response_dict:
        #    return response_dict
        #else:
        response = requests.get("%s%s"%(self.BASE_URL, method), params=request_params,
                proxies=proxies)
        response_dict = response.json()
        self._check_for_errors(response_dict)
        #self._cache.save_request(method, params, response_dict)
        return response_dict

        #if self._caching and os.path.isfile(dump_file):
        #    self._logger.info("Loading request form %s" % dump_file)
        #    with open(dump_file, "r") as f:
        #        response_dict = json.load(f)
        #else:
        #    response = requests.get("%s%s"%(self.BASE_URL, method), params=request_params,
        #            proxies=proxies)
        #    self._logger.info("YOUTUBE_REQUEST: URL %s" % response.url)
        #    response_dict = response.json()
        #    self._check_for_errors(response_dict)
        #    if self._caching:
        #        self._logger.info("Saving request to %s" % dump_file)
        #        with open(dump_file, "w") as f:
        #            json.dump(response_dict, f)
        #return response_dict

    def search(self, channel_id="", search_query="", duration="",
            part='snippet', order="date", max_results=50, type="video",
            published_after="", published_before="", event_type="", page_token="" ):

        params = {
                'part':part,
                'order':order,
                'maxResults':max_results,
                'type':type,
        }

        if search_query:
            params.update({'q': search_query})
        if channel_id:
            params.update({'channelId': channel_id})
        if published_before:
            params.update({'publishedBefore': published_before})
        if published_after:
            params.update({'publishedAfter': published_after})
        if page_token:
            params.update({'pageToken': page_token})
        if duration:
            params.update({'videoDuration': duration})
        if event_type:
            params.update({'eventType': event_type})

        return self._request("search", params)

    def channels(self, channel_ids, max_results=50, page_token="", part='snippet'):
        params = { 'part':part,
                'maxResults':max_results,
                'id':",".join(channel_ids),
                }
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("channels", params)

    def videos(self, video_ids, max_results=50, page_token="",
            part='snippet,contentDetails'):
        params = { 'part':part,
                'maxResults':max_results,
                'id':",".join(video_ids),
                }
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("videos", params)

    def search_all(self, channel_id="", search_query="", duration=None, published_before=None,
            published_after=None, event_type="", page_token=None, part="snippet"):
        """ make a search request to youtube api v3, but returns a list of all
            items, instead of pages.
            returns:
                list: of all response['items']. see youtube api documentation.
        """
        self._logger.info("Fetching ALL videos data from youtube.")
        search_params = dict(channel_id=channel_id, search_query=search_query,
                page_token=page_token, duration=duration, published_after=published_after,
                published_before=published_before, event_type=event_type,
                part=part)
        yt_response = self.search(**search_params)
        videos = []
        while yt_response['items']:
            videos.extend(yt_response['items'])
            try:
                search_params['page_token'] = yt_response['nextPageToken']
                yt_response = self.search(**search_params)
            except KeyError:
                break
        self._logger.info("Fetched ALL (%i) videos from youtube." % len(videos))
        #!TODO: return error
        return videos

    def channels_all(self, channel_ids=(), part="snippet,contentDetails"):
        """ make a channels request to youtube api v3, but returns a list of all
            items, instead of pages.
            returns:
                list: of all response['items']. with contentDetails.
                                                see youtube api documentation.
        """
        max_results = 50
        start_idx = 0
        end_idx = max_results
        channels = []
        while len(channel_ids[start_idx:end_idx]):
            response = self.channels(channel_ids[start_idx:end_idx], part=part)
            channels.extend(response['items'])
            start_idx += max_results
            end_idx += max_results
        return channels

    def videos_all(self, video_ids=(), part="snippet,contentDetails"):
        """ make a videos request to youtube api v3, but returns a list of all
            items, instead of pages.
            returns:
                list: of all response['items']. with contentDetails.
                                                see youtube api documentation.
        """
        max_results = 50
        start_idx = 0
        end_idx = max_results
        videos = []
        while len(video_ids[start_idx:end_idx]):
            response = self.videos(video_ids[start_idx:end_idx], part=part)
            videos.extend(response['items'])
            start_idx += max_results
            end_idx += max_results
        return videos

class YoutubeVideo:
    URL_BASE = "http://youtube.de/watch?v="

    def __init__(self, title, description, image_url, video_id, duration=None,
            published_at=None, live_broadcast=None, channel_id=None):
        self.title = title
        self.description = description
        self.image_url = image_url
        self.video_id = video_id
        self.duration = duration
        self.published_at = published_at
        self.live_broadcast = live_broadcast
        self.channel_id = channel_id

    def url(self):
        return self.URL_BASE + self.video_id

class YoutubeChannel:
    def __init__(self, title, description, channel_id, image):
        self.title = title
        self.description = description
        self.channel_id = channel_id
        self.image = image


class YoutubeFinder:
    def __init__(self, developer_key, dump_dir=None, logger=None):
        self._logger = logger if logger else logging
        self._api = YoutubeAPI(developer_key, dump_dir=dump_dir, logger=self._logger)

    def get_channels(self, channel_ids=()):
        """ get channels information.
            params:
                list: channel ids
            returns:
                list: YoutubeChannel

        """
        items = self._api.channels_all(channel_ids)
        channels = []
        for channel in items:
            snippet = channel['snippet']
            channels.append(
                    YoutubeChannel(
                        snippet['title'],
                        snippet['description'],
                        channel['id'],
                        snippet['thumbnails']['medium']['url']
                    )
            )
        return channels

    def get_channel(self, channel_id):
        return self.get_channels((channel_id, ))[0]

    def search_videos(self, channel_id="", search_query="", duration=None, published_before=None,
            published_after=None, event_type=""):
        """ search for videos.
            returns:
                list: YoutubeVideo
        """
        response_items = self._api.search_all(channel_id = channel_id,
                search_query=search_query, duration=duration,
                published_before=published_before,
                published_after=published_after, event_type=event_type)
        videos = [
            YoutubeVideo(
                v['snippet']['title'],
                v['snippet']['description'],
                v['snippet']['thumbnails']['medium']['url'],
                v['id']['videoId'],
                published_at=v['snippet']['publishedAt'],
                live_broadcast=v['snippet']['liveBroadcastContent'],
                channel_id=v['snippet']['channelId']
            )
            for v in response_items
        ]
        return videos

    def get_videos(self, channel_id="", search_query="", duration=None, published_before=None,
            published_after=None, event_type="" ):
        """ get videos with all informations form search.
            returns:
                list: YoutubeVideo
        """
        # get video_ids for search
        videos = self._api.search_all(part="id", channel_id=channel_id,
                search_query=search_query, duration=duration,
                event_type=event_type,
                published_before=published_before,
                published_after=published_after)
        video_ids = [v['id']['videoId'] for v in videos]
        # get detail information for each video
        video_items = self._api.videos_all(video_ids=video_ids)
        videos = [
            YoutubeVideo(
                v['snippet']['title'],
                v['snippet']['description'],
                v['snippet']['thumbnails']['medium']['url'],
                v['id'],
                duration=v['contentDetails']['duration'],
                published_at=v['snippet']['publishedAt'],
                live_broadcast=v['snippet']['liveBroadcastContent'],
                channel_id=v['snippet']['channelId']
            )
            for v in video_items
        ]
        return videos
