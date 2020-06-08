
import logging
from datetime import timedelta
import requests
from video_finder.video_finder import YoutubeAPI


logging.basicConfig(level=logging.DEBUG)
_DEVELOPER_KEY = "fake-dev-key"
finder = YoutubeAPI(_DEVELOPER_KEY, caching=False,
                    caching_delay=timedelta(seconds=10.0))


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


def test_search(monkeypatch):
    search_query = "py test"
    expected_params = {
            'part': 'snippet',
            'maxResults': '50',
            'q': search_query,
            'order': 'date',
            'type': 'video',
            'videoDuration': 'any',
            'key': 'fake-dev-key'}
    expected_endpoint = f"{YoutubeAPI.BASE_URL}search"
    _test_params(monkeypatch, expected_params, expected_endpoint)
    finder.search(search_query=search_query)


def test_channles(monkeypatch):
    search_for_ids = ("UCcIvNGMBSQWwo1v3n-ZRBCw", "UCHemJpLUcATaKqDzohNAa6A")
    expected_params = {
            'part': 'snippet',
            'maxResults': '50',
            'id': ','.join(search_for_ids),
            'key': 'fake-dev-key'}
    expected_endpoint = f"{YoutubeAPI.BASE_URL}channels"

    _test_params(monkeypatch, expected_params, expected_endpoint)
    finder.channels(search_for_ids)
    expected_params = {
            'part': 'snippet',
            'maxResults': '5',
            'id': ','.join(search_for_ids),
            'pageToken': "ABC",
            'key': 'fake-dev-key'}

    _test_params(monkeypatch, expected_params, expected_endpoint)
    finder.channels(search_for_ids, max_results=5, page_token="ABC")


def test_videos(monkeypatch):
    search_for_ids = ("zhkFscdoMbs", "C4sZyLmQvWM")

    expected_params = {
            'part': 'snippet,contentDetails',
            'maxResults': '50',
            'id': ','.join(search_for_ids),
            'key': 'fake-dev-key'}

    expected_endpoint = f"{YoutubeAPI.BASE_URL}videos"
    _test_params(monkeypatch, expected_params, expected_endpoint)
    finder.videos(search_for_ids)
    expected_params = {
            'part': 'snippet',
            'maxResults': '5',
            'id': ','.join(search_for_ids),
            'pageToken': "ABC",
            'key': 'fake-dev-key'}

    _test_params(monkeypatch, expected_params, expected_endpoint)
    finder.videos(search_for_ids, max_results=5, page_token="ABC",
                  part="snippet")


def test_search_all():
    pass


def test_channels_all():
    pass


def test_videos_all():
    pass





