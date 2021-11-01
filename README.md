# simple-youtube-video-finder
get public video data from youtube. 

## example

```python
from video_finder import video_finder

finder = video_finder.YoutubeFinder("my-api-key")
videos = finder.search_videos(search_query="summon python", content_details=True)
for v in videos:
    print(f"{v.title} - {v.duration}")
```
TODO: full example

## supported search parameter 

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

## Run Test
```bash
export YOUTUBE_API_KEY=Your-Api-Key-abcdefg
python -m pytest tests --verbose
```

## TODO
- [ ] more examples
- [ ] better tests
- [ ] parse duration
- [ ] parse published_at
