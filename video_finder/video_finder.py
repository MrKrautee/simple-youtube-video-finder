import os
import json
import requests
import hashlib
import logging
from typing import List, Dict, Any, Tuple
from enum import Enum
from datetime import datetime
from datetime import timedelta

__all__ = ["VideoDuration", "ResultType", "VideoEmbeddable", "VideoCaption",
           "VideoDefinition", "Order", "EventType", "YoutubeAPI",
           "YoutubeVideo", "YoutubeChannel", "YoutubeFinder"]


class VideoDuration(Enum):
    """ The videoDuration parameter filters video search results based on their
        duration. If you specify a value for this parameter, you must also set
        the type parameter's value to video.
    """
    ANY = "any"  # do not filter on duration (default)
    LONG = "long"  # videos longer than 20 mins.
    MEDIUM = "medium"  # videos between 4 and 20 mins.
    SHORT = "short"  # videos less than 4 mins.


class ResultType(Enum):
    """ The type parameter restricts a search query to only retrieve a
        particular type of resource.
    """
    CHANNEL = "channel"
    PLAYLIST = "playlist"
    VIDEO = "video"


class VideoEmbeddable(Enum):
    """ The videoEmbeddable parameter lets you to restrict a search to only
        videos that can be embedded into a webpage. If you specify a value
        for this parameter, you must also set the type parameter's value to
        video.
    """
    ANY = "any"
    TRUE = "true"


class VideoCaption(Enum):
    """ The videoCaption parameter indicates whether the API should filter
        video search results based on whether they have captions. If you
        specify a value for this parameter, you must also set the type
        parameter's value to video.
    """
    ANY = "any"
    CLOSEDCAPTION = "closedCaption"  # videos that have caption
    NONE = "none"  # videos that do not have caption


class VideoDefinition(Enum):
    ANY = "any"
    HIGH = "high"
    STANDARD = "standard"


class Order(Enum):
    DATE = "date"
    RATING = "rating"
    RELEVANCE = "relevance"
    TITLE = "title"
    VIDEOCOUNT = "videoCount"
    VIEWCOUNT = "viewCount"


class EventType(Enum):
    COMPLETED = "completed"
    LIVE = "live"
    UPCOMING = "upcoming"


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
            param_str_list = [f"{key}:{value}"
                              for key, value in params.items()]
            to_hash = (method+','.join(param_str_list)).encode("utf-8")
            self._logger.debug(f"Create hash from {to_hash}")
            request_hash = hashlib.sha224(to_hash).hexdigest()
            # ? is request cached
            if request_hash in self._cache.keys():
                time_str, response_json = self._cache[request_hash]
                # only use not expired requests
                time = datetime.fromisoformat(time_str)
                if datetime.now() - time < self._expires:
                    self._logger.info(f"Loading request {request_hash}")
                    return response_json
                else:
                    self._logger.debug(f"Expired request {request_hash}")
            # response not cached!
            response_json = func(method, params)
            # cache it
            self._logger.info(f"Caching request {request_hash}")
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
        proxies = {"http": None, "https": None}
        response = requests.get("%s%s" % (self.BASE_URL, method),
                                params=request_params, proxies=proxies)
        self._logger.info("request url: %s" % response.url)
        response_dict = response.json()
        self._check_for_errors(response_dict)
        return response_dict

    def search(self,
               channel_id: str = "",
               search_query: str = "",
               order: Order = Order.DATE,
               max_results: int = 50,
               published_after: datetime = None,
               published_before: datetime = None,
               relevance_language: str = "",
               result_type: List[ResultType] = (ResultType.VIDEO,),
               part='snippet',
               page_token: str = "",
               # video only
               event_type: EventType = None,
               duration: VideoDuration = None,
               caption: VideoCaption = None,
               embeddable: VideoEmbeddable = None,
               definition: VideoDefinition = None,
               related_to_video_id: str = "") -> Dict[str, Any]:
        """ make /search request to www.googleapis.com/youtube/v3.
            Args:
                channel_id (str): channel to search in.
                search_query (str): search term.
                order (Order): ordering of the search result.
                max_results: results per page.
                published_before (datetime): utc datetime.
                    (ie: datetime.datetime.utcnow())
                published_after (datetime): utc datetime.
                    (ie: datetime.datetime.utcnow())
                relevance_language (str): The relevanceLanguage parameter
                    instructs the API to return search results that are most
                    relevant to the specified language. The parameter value is
                    typically an ISO 639-1 two-letter language code.
                result_type (ResultType): what resource you searching for.
                part (str)
                page_token (str)
                event_type (EventType): broadcast or not?
                    (only for result_type: video)
                duration (VideoDuration): (only for result_type: video)
                caption (VideoCaption)
                embeddable (VideoEmbeddable)
                definition (VideoDefinition)
                related_to_video_id (str): The relatedToVideoId parameter
                    retrieves a list of videos that are related to the video
                    that the parameter value identifies.
            Returns:
                dict:
                    youtube response, see
                    https://developers.google.com/youtube/v3/docs/search/list#response
        """

        params = {
                'part': part,
                'order': order.value,
                'maxResults': max_results,
                'type': ','.join(map(lambda e: e.value, result_type)),
        }

        if search_query:
            params.update({'q': search_query})
        if channel_id:
            params.update({'channelId': channel_id})
        if published_before:
            published_before_tz = published_before.astimezone()
            before_rfc3339 = published_before_tz.isoformat()
            params.update({'publishedBefore': before_rfc3339})
        if published_after:
            published_after_tz = published_after.astimezone()
            after_rfc3339 = published_after_tz.isoformat()
            params.update({'publishedAfter': after_rfc3339})
        if relevance_language:
            params.update({'relevanceLanguage': relevance_language})
        if page_token:
            params.update({'pageToken': page_token})
        if event_type:
            params.update({'eventType': event_type.value})
        if duration:
            params.update({'videoDuration': duration.value})
        if caption:
            params.update({'videoCaption': caption.value})
        if embeddable:
            params.update({'videoEmbeddable': embeddable.value})
        if definition:
            params.update({'videoDefinition': definition.value})
        if related_to_video_id:
            params.update({'relatedToVideoId': related_to_video_id})

        return self._request("search", params)

    def channels(self, channel_ids, max_results=50, page_token="",
                 part='snippet') -> Dict[str, Any]:
        """ make /channels request to www.googleapis.com/youtube/v3.
            look at youtube api documentation:
            https://developers.google.com/youtube/v3/docs/channels/list
        """
        params = {'part': part,
                  'maxResults': max_results,
                  'id': ",".join(channel_ids)}
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("channels", params)

    def videos(self, video_ids, max_results=50, page_token="",
               part='snippet,contentDetails') -> Dict[str, Any]:
        """ make /videos request to www.googleapis.com/youtube/v3.
            look at youtube api documentation:
            https://developers.google.com/youtube/v3/docs/videos/list
        """
        params = {'part': part,
                  'maxResults': max_results,
                  'id': ",".join(video_ids)}
        if page_token:
            params.update({'pageToken': page_token})

        return self._request("videos", params)

    def search_all(self,
                   channel_id: str = "",
                   search_query: str = "",
                   order: Order = Order.DATE,
                   published_after: datetime = None,
                   published_before: datetime = None,
                   relevance_language: str = "",
                   result_type: List[ResultType] = (ResultType.VIDEO,),
                   part='snippet',
                   # video only
                   event_type: EventType = None,
                   duration: VideoDuration = None,
                   caption: VideoCaption = None,
                   embeddable: VideoEmbeddable = None,
                   definition: VideoDefinition = None,
                   related_to_video_id: str = "") -> List[Dict[str, Any]]:
        """ make a search request to youtube api v3, but returns a list of all
            items, instead of pages.
            returns:
                list: of all response['items']. see youtube api documentation.
        """
        self._logger.info("Fetching ALL videos data from youtube.")
        search_params = dict(channel_id=channel_id, search_query=search_query,
                             order=order, published_after=published_after,
                             published_before=published_before,
                             relevance_language=relevance_language,
                             result_type=result_type, part=part,
                             event_type=event_type, duration=duration,
                             caption=caption, embeddable=embeddable,
                             definition=definition,
                             related_to_video_id=related_to_video_id)
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
        return videos

    def channels_all(self, channel_ids: Tuple[str] = (),
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

    def videos_all(self, video_ids: Tuple[str] = (),
                   part="snippet,contentDetails") -> List[Dict[str, Any]]:
        """ make a /videos request to youtube api v3, but returns a list of all
            items, instead of pages.
            Returns:
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
    # maps attributes to response values
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
            raise AttributeError(
                    f"can't access '{name}' from response object."
            )

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
            'published_at': ['snippet', 'publishedAt'],
            'live_broadcast': ['snippet', 'liveBroadcastContent'],
            'channel_id': ['snippet', 'channelId'],
            'channel_title': ['snippet', 'channelTitle'],
            'etag': ['etag'],
            # only with content_details=True
            'duration': ['contentDetails', 'duration'],
            'definition': ['contentDetails', 'definition'],
            'dimension': ['contentDetails', 'demension'],
            'tags': ['snippet', 'tags']
    }

    def __init__(self, raw):
        super().__init__(raw)
        # response for /videos is different from /search.
        if self._raw['kind'] == "youtube#video":
            self.fields['video_id'] = ['id']

    @property
    def url(self) -> str:
        return self.URL_BASE + self.video_id


class YoutubeChannel(ResponseAndapter):
    URL_BASE = "http://youtube.de/channel/"
    fields = {
            'title': ['snippet', 'title'],
            'description': ['snippet', 'description'],
            'image_url': ['snippet', 'thumbnails', 'medium', 'url'],
            'published_at': ['snippet', 'publishedAt'],
            'custom_url': ['snippet', 'customUrl'],
            'channel_id': ['id'],
            'etag': ['etag'],
            'country': ['country'],
    }

    @property
    def url(self) -> str:
        return self.URL_BASE + self.video_id


class YoutubeFinder:
    def __init__(self, developer_key, dump_dir=None, logger=None, caching=True,
                 caching_delay=timedelta(days=1.0)):
        self._logger = logger if logger else logging.getLogger(__name__)
        self._api = YoutubeAPI(developer_key, dump_dir=dump_dir,
                               logger=self._logger, caching=caching,
                               caching_delay=caching_delay)

    def get_channels(self,
                     channel_ids: Tuple[str] = ()) -> List[YoutubeChannel]:
        """ get channels information.
            Args:
                channel_id (tuple): channel ids
            Returns:
                List[YoutubeChannel]:
                    List with requested channels.

        """
        items = self._api.channels_all(channel_ids)
        channels = []
        for channel in items:
            channels.append(YoutubeChannel(channel))
        return channels

    def get_channel(self, channel_id: str) -> YoutubeChannel:
        return self.get_channels((channel_id, ))[0]

    def search_videos(self, content_details=False,
                      # search params
                      channel_id: str = "",
                      search_query: str = "",
                      order: Order = Order.DATE,
                      published_after: datetime = None,
                      published_before: datetime = None,
                      relevance_language: str = "",
                      event_type: EventType = None,
                      duration: VideoDuration = None,
                      caption: VideoCaption = None,
                      embeddable: VideoEmbeddable = None,
                      definition: VideoDefinition = None,
                      related_to_video_id: str = "") -> List[YoutubeVideo]:
        """ Search for videos.
            Args:
                content_details (bool): detail information for each video
                    (needs extra requests, default is False).
                channel_id (str): channel to search in.
                search_query (str): search term.
                order (Order): ordering of the search result.
                published_before (datetime): utc datetime.
                    (ie: datetime.datetime.utcnow())
                published_after (datetime): utc datetime.
                    (ie: datetime.datetime.utcnow())
                relevance_language (str): The relevanceLanguage parameter
                    instructs the API to return search results that are most
                    relevant to the specified language. The parameter value is
                    typically an ISO 639-1 two-letter language code.
                event_type (EventType): broadcast or not?
                    (only for result_type: video)
                duration (VideoDuration): (only for result_type: video)
                caption (VideoCaption)
                embeddable (VideoEmbeddable)
                definition (VideoDefinition)
                related_to_video_id (str): The relatedToVideoId parameter
                    retrieves a list of videos that are related to the video
                    that the parameter value identifies.
            Returns:
                List[YoutubeVideo]:
                    search result containing all matching videos.
        """
        part = "id" if content_details else "snippet"
        response_items = self._api.search_all(
                            part=part,
                            channel_id=channel_id, search_query=search_query,
                            order=order, published_before=published_before,
                            published_after=published_after,
                            relevance_language=relevance_language,
                            event_type=event_type, duration=duration,
                            caption=caption, embeddable=embeddable,
                            definition=definition,
                            related_to_video_id=related_to_video_id
        )
        if content_details:  # get addtional video data (contentDetails)
            video_ids = [v['id']['videoId'] for v in response_items]
            self._logger.info(f"get contentDetails for {video_ids}")
            # get detail information for each video
            response_items = self._api.videos_all(video_ids=video_ids)

        videos = [YoutubeVideo(v) for v in response_items]
        return videos
