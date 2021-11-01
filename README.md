# simple-youtube-video-finder
Very simple interface for Youtube API v3 to fetch public video data.
No need for OAuth2.0 or many dependencies (needs only `requests`).

Having some auth issues with the official api [googleapis/google-api-python-client](https://github.com/googleapis/google-api-python-client) and just for fun,
I ended up coding this easy api for my simple needs.
used in [MrKrautee/video-gatherer](https://github.com/MrKrautee/django-video-gatherer).

## Features
* fetches public youtube video data
* implements following endpoints:
    * [search/list](https://developers.google.com/youtube/v3/docs/search/list)
    * [videos/list](https://developers.google.com/youtube/v3/docs/videos/list)
    * [channels/list](https://developers.google.com/youtube/v3/docs/channels/list)
* option to cache requests for development ('safe quota')
* option to fetch all search results at once
* option to include detailed video informations, 'contentDetails' (uses more quota)

## Usage

```python
from video_finder import video_finder

finder = video_finder.YoutubeFinder("my-api-key")
videos = finder.search_videos(search_query="summon python", content_details=True)
for v in videos:
    print(f"{v.title} - {v.duration}")
```
Read the code for more details:

`YoutubeFinder` will return those types in a list:
* [Video Return Type](https://github.com/MrKrautee/simple-youtube-video-finder/blob/46aa8bfeaa993be3edfd34e23237879ce19afeeb/video_finder/video_finder.py#L394) 
* [Channel Return Type](https://github.com/MrKrautee/simple-youtube-video-finder/blob/46aa8bfeaa993be3edfd34e23237879ce19afeeb/video_finder/video_finder.py#L424)

`YoutubeAPI` will return the raw response from the youtube rest api.

As I mentioned, read the sources for further information:
[video_finder.py](https://github.com/MrKrautee/simple-youtube-video-finder/blob/master/video_finder/video_finder.py)

### Supported Search Params

for all searches:
|supported ?| param name|
|-----------|-----------|
| x  | part(required)   |
| x  | channelId |
| x  | channelType  |
| x  | maxResults |
| x  | order |
| x  | pageToken |
| x  | published_after |
| x  | published_befor |
| x  | q |
| x  | type |
|    | regionCode |
| x  | relevanceLanguage |
|    | safeSearch  |
|    | location |
|    | locationRadius |

only for video searches:
|supported ?| param name|
|-----------|-----------|
| x  |  eventType |
| x  |  videoCaption |
| x  |  videoDuration |
| x  |  videoEmbeddable |
|    |  videoLicense  |
|    |  videoSyndicated  |
|    |  videoType  |
| x  |  videoDefinition  |
|    |  videoDimension  |
| x  |  relatedToVideoId |
|    |  videoCategoryId |

## Development
### Run Tests
```bash
$ export YOUTUBE_API_KEY=Your-Api-Key-abcdefg
$ python -m pytest tests --verbose
```

## Resources
* [YouTube Data API v3 Documentation](https://developers.google.com/youtube/v3/docs)
* [Developer Console](https://console.developers.google.com/) to get yout API
  key
