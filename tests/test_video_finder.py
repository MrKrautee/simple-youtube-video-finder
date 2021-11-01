import os
import logging
from datetime import timedelta
from datetime import datetime
import requests
from video_finder.video_finder import YoutubeAPI, YoutubeFinder
from video_finder.video_finder import Order
from video_finder.video_finder import VideoDuration
from video_finder.video_finder import VideoEmbeddable, EventType
from video_finder.video_finder import VideoDefinition, VideoCaption


logging.basicConfig(level=logging.DEBUG)
_DEVELOPER_KEY = "fake-dev-key"

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

search_query = {
        "exactly_one": dict(
            channel_id="UC3slESOJpcy6rBYq7v_QAVA",
            search_query="MrKrautee"),
        "all_video_params": dict(
                     channel_id="UCV73LMcuZQfH5If9JBFb43Q",
                     search_query="Yoga",
                     order=Order.RATING,
                     published_before=datetime.utcnow(),
                     relevance_language="de",
                     event_type=EventType.COMPLETED,
                     duration=VideoDuration.ANY,
                     caption=VideoCaption.ANY,
                     embeddable=VideoEmbeddable.TRUE,
                     definition=VideoDefinition.ANY,
                     related_to_video_id="KkXrClafQYo"
        )

}


class MockResponse:

    @staticmethod
    def json():
        return {"mock_key": "mock_response"}

    url = "https://fake/url/for/test/"


def _test_params(monkeypatch, expected_params, expected_endpoint):
    def mock_get(*args, **kwargs):
        endpoint = args[0]
        params = kwargs['params']
        assert endpoint == expected_endpoint
        assert params == expected_params
        return MockResponse()

    # apply the monkeypatch for requests.get to mock_get
    monkeypatch.setattr(requests, "get", mock_get)


class TestYoutubeAPI:

    api = YoutubeAPI(YOUTUBE_API_KEY, caching=False,
                     caching_delay=timedelta(seconds=10.0))

    def test_search(self, monkeypatch):
        search_query = "py test"
        expected_params = {
                'part': 'snippet',
                'maxResults': '50',
                'q': search_query,
                'order': 'date',
                'type': 'video',
                'key': YOUTUBE_API_KEY}
        expected_endpoint = f"{YoutubeAPI.BASE_URL}search"
        _test_params(monkeypatch, expected_params, expected_endpoint)
        self.api.search(search_query=search_query)

    def test_channles(self, monkeypatch):
        search_for_ids = ("UCcIvNGMBSQWwo1v3n-ZRBCw",
                          "UCHemJpLUcATaKqDzohNAa6A")
        expected_params = {
                'part': 'snippet',
                'maxResults': '50',
                'id': ','.join(search_for_ids),
                'key': YOUTUBE_API_KEY}
        expected_endpoint = f"{YoutubeAPI.BASE_URL}channels"

        _test_params(monkeypatch, expected_params, expected_endpoint)
        self.api.channels(search_for_ids)
        expected_params = {
                'part': 'snippet',
                'maxResults': '5',
                'id': ','.join(search_for_ids),
                'pageToken': "ABC",
                'key': YOUTUBE_API_KEY}

        _test_params(monkeypatch, expected_params, expected_endpoint)
        self.api.channels(search_for_ids, max_results=5, page_token="ABC")

    def test_videos(self, monkeypatch):
        search_for_ids = ("zhkFscdoMbs", "C4sZyLmQvWM")

        expected_params = {
                'part': 'snippet,contentDetails',
                'maxResults': '50',
                'id': ','.join(search_for_ids),
                'key': YOUTUBE_API_KEY}

        expected_endpoint = f"{YoutubeAPI.BASE_URL}videos"
        _test_params(monkeypatch, expected_params, expected_endpoint)
        self.api.videos(search_for_ids)
        expected_params = {
                'part': 'snippet',
                'maxResults': '5',
                'id': ','.join(search_for_ids),
                'pageToken': "ABC",
                'key': YOUTUBE_API_KEY}

        _test_params(monkeypatch, expected_params, expected_endpoint)
        self.api.videos(search_for_ids, max_results=5, page_token="ABC",
                        part="snippet")

    def test_search_all(self, monkeypatch):
        videos = self.api.search_all(**search_query['exactly_one'])
        assert len(videos) == 1

    def test_channels_all(self, monkeypatch):
        pass

    def test_videos_all(self, monkeypatch):
        pass


class TestYoutubeFinder:

    finder = YoutubeFinder(YOUTUBE_API_KEY)

    def test_search_videos(self):
        """ after now() should bring no results, at least
            in this channel with this search term.

            it seems that sometime published_after not working.
            youtube rest bug? or wrong formatted datetime?
        """
        videos = self.finder.search_videos(
                content_details=True,
                channel_id="UCBC3nbpRi7ZpM2MwT5HlGZA",
                search_query="THE CREW2",
                published_after=datetime.utcnow()
        )
        assert len(videos) == 0

    def test_search_params(self):
        videos = self.finder.search_videos(**search_query['all_video_params'])
        assert len(videos) > 0
