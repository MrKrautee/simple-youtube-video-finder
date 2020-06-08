import os
import json
import requests
import hashlib
import logging
from typing import List, Dict, Any
from datetime import datetime
from datetime import timedelta


class YoutubeAPIException(Exception):
    def __init__(self, response):
        super().__init__(response['error']['message'])


class YoutubeAPI:
    BASE_URL = "https://www.googleapis.com/youtube/v3/"
    DUMP_FILE_NAME = ".request_cache.json"
    DUMP_DIR = "."

    def __init__(self, developer_key, dump_dir=".", logger=None, caching=True,
                 caching_delay=timedelta(days=1.0)):
        self._developer_key = developer_key
        self._logger = logger if logger else logging.getLogger(__name__)
        if caching:
            if not dump_dir:
                dump_dir = self.DUMP_DIR
            try:
                os.mkdir(dump_dir)
            except FileExistsError:
                pass
            self._expires = caching_delay
            self._cache_file = "%s/%s" % (os.path.abspath(dump_dir),
                                          self.DUMP_FILE_NAME)
            # Load cache from file
            cache = {}
            if os.path.isfile(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    cached_requests = json.load(f)
                    for request_hash, (time_str, response) \
                            in cached_requests.items():
                        time = datetime.fromisoformat(time_str)
                        if datetime.now() - time < self._expires:
                            cache[request_hash] = (time_str, response)
            self._cache = cache
            self._request = self._cached_request(self._request)

    def _cached_request(self, func):
        def do_caching(method="", params={}):
            # generate hash of the request, used as identifier
            params = {str(key): str(value) for key, value in params.items()}
            to_hash = (method+''.join(params.values())).encode("utf-8")
            request_hash = hashlib.sha224(to_hash).hexdigest()
            # ? is request cached
            if request_hash in self._cache.keys():
                time_str, response_json = self._cache[request_hash]
                # only use not expired requests
                time = datetime.fromisoformat(time_str)
                if datetime.now() - time < self._expires:
                    self._logger.info("Loading request ")
                    return response_json
            # response not cached!
            response_json = func(method, params)
            # cache it
            self._logger.info("Saving request ")
            self._cache[request_hash] = (str(datetime.now()), response_json)
            # write to file, in case of sudden termination of the script
            # __del__ not relyable!
            with open(self._cache_file, 'w') as f:
                json.dump(self._cache, f)
            return response_json
        return do_caching

    def _check_for_errors(self, response):
        if 'error' in response.keys():
            raise YoutubeAPIException(response)

    def _request(self, method="search", params=dict()) -> Dict[str, Any]:
        # some search params maybe int ...
        params = {str(key): str(value) for key, value in params.items()}
        request_params = {
                **params,
                'key': self._developer_key,
        }
        # disable proxy for faster response
        proxies = {
            "http": None,
            "https": None,
        }
        response = requests.get("%s%s" % (self.BASE_URL, method),
                                params=request_params, proxies=proxies)
        self._logger.info("request url: %s" % response.url)
        response_dict = response.json()
        self._check_for_errors(response_dict)
        return response_dict

    def search(self, channel_id="", search_query="", duration="",
               part='snippet', order="date", max_results=50, type="video",
               published_after="", published_before="", event_type="",
               page_token="") -> Dict[str, Any]:

        params = {
                'part': part,
                'order': order,
                'maxResults': max_results,
                'type': type,
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

    def channels(self, channel_ids, max_results=50, page_token="",
                 part='snippet') -> Dict[str, Any]:
        params = {'part': part,
                  'maxResults': max_results,
                  'id': ",".join(channel_ids)}
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("channels", params)

    def videos(self, video_ids, max_results=50, page_token="",
               part='snippet,contentDetails') -> Dict[str, Any]:
        params = {'part': part,
                  'maxResults': max_results,
                  'id': ",".join(video_ids)}
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("videos", params)

    def search_all(self, channel_id="", search_query="", duration=None,
                   published_before=None, published_after=None, event_type="",
                   page_token=None, part="snippet") -> List[Dict[str, Any]]:
        """ make a search request to youtube api v3, but returns a list of all
            items, instead of pages.
            returns:
                list: of all response['items']. see youtube api documentation.
        """
        self._logger.info("Fetching ALL videos data from youtube.")
        search_params = dict(channel_id=channel_id, search_query=search_query,
                             page_token=page_token, duration=duration,
                             published_after=published_after,
                             published_before=published_before,
                             event_type=event_type, part=part)
        yt_response = self.search(**search_params)
        videos = []
        while yt_response['items']:
            videos.extend(yt_response['items'])
            try:
                search_params['page_token'] = yt_response['nextPageToken']
                yt_response = self.search(**search_params)
            except KeyError:
                # got all pages, no next page
                break
        self._logger.info(
                "Fetched ALL (%i) videos from youtube." % len(videos)
        )
        # !TODO: return error
        return videos

    def channels_all(self, channel_ids=(),
                     part="snippet,contentDetails") -> List[Dict[str, Any]]:
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

    def videos_all(self, video_ids=(),
                   part="snippet,contentDetails") -> List[Dict[str, Any]]:
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


class ResponseAndapter:
    fields: Dict[str, list] = {}

    def __init__(self, response_item):
        self._raw = response_item

    def _get_value(self, key_list: list, response_element: dict) -> str:
        key = key_list[0]
        value = response_element[key]
        if key_list[1:]:
            return self._get_value(key_list[1:], value)
        else:
            return value

    def __getattr__(self, name) -> str:
        try:
            return self._get_value(self.fields[name], self._raw)
        except KeyError:
            raise AttributeError(f"cant access '{name}' from response")

    @property
    def raw(self) -> dict:
        return self._raw


class YoutubeVideo(ResponseAndapter):
    URL_BASE = "http://youtube.de/watch?v="
    fields = {
            'title': ['snippet', 'title'],
            'description': ['snippet', 'description'],
            'image_url': ['snippet', 'thumbnails', 'medium', 'url'],
            'video_id': ['id', 'videoId'],
            'duration': ['contentDetails', 'duration'],
            'published_at': ['snippet', 'publishedAt'],
            'live_broadcast': ['snippet', 'liveBroadcastContent'],
            'channel_id': ['snippet', 'channelId'],
            'channel_title': ['snippet', 'channelTitle'],
            'etag': ['etag'],
    }

    def url(self) -> str:
        return self.URL_BASE + self.video_id


class YoutubeChannel:
    URL_BASE = "http://youtube.de/channel/"
    fields = {
            'title': ['snippet', 'title'],
            'description': ['snippet', 'description'],
            'image_url': ['snippet', 'thumbnails', 'medium', 'url'],
            'published_at': ['snippet', 'publishedAt'],
            'live_broadcast': ['snippet', 'liveBroadcastContent'],
            'channel_id': ['id'],
            'etag': ['etag'],
            'country': ['country'],
    }

    def url(self) -> str:
        return self.URL_BASE + self.video_id


class YoutubeFinder:
    # @TODO: caching
    def __init__(self, developer_key, dump_dir=None, logger=None):
        self._logger = logger if logger else logging
        self._api = YoutubeAPI(developer_key, dump_dir=dump_dir,
                               logger=self._logger)

    def get_channels(self, channel_ids=()) -> List[YoutubeChannel]:
        """ get channels information.
            params:
                list: channel ids
            returns:
                list: YoutubeChannel

        """
        items = self._api.channels_all(channel_ids)
        channels = []
        for channel in items:
            channels.append(YoutubeChannel(channel))
        return channels

    def get_channel(self, channel_id) -> YoutubeChannel:
        return self.get_channels((channel_id, ))[0]

    def search_videos(self, channel_id="", search_query="", duration=None,
                      published_before=None, published_after=None,
                      event_type="") -> List[YoutubeVideo]:
        """ search for videos.
            returns:
                list: YoutubeVideo
        """
        response_items = self._api.search_all(
                            channel_id=channel_id, search_query=search_query,
                            duration=duration,
                            published_before=published_before,
                            published_after=published_after,
                            event_type=event_type)
        videos = [YoutubeVideo(v) for v in response_items]
        return videos

    def get_videos(self, channel_id="", search_query="", duration=None,
                   published_before=None, published_after=None,
                   event_type="") -> List[YoutubeVideo]:
        """ get videos with all informations form search.
            returns:
                list: YoutubeVideo
        """
        # get video_ids for search
        videos = self._api.search_all(
                    part="id", channel_id=channel_id,
                    search_query=search_query, duration=duration,
                    event_type=event_type,
                    published_before=published_before,
                    published_after=published_after)
        video_ids = [v['id']['videoId'] for v in videos]
        # get detail information for each video
        video_items = self._api.videos_all(video_ids=video_ids)
        videos = [YoutubeVideo(v) for v in video_items]
        return videos
