import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError

from .m3u8_sniffer import get_m3u8_url_and_headers, M3U8SnifferError


class KissAsianIE(InfoExtractor):
    IE_NAME = "kissasian"
    IE_DESC = "kissasian.cam"

    _VALID_URL = r"https?://(?:www\.)?kissasian\.cam/(?P<id>[^/?#]+)"

    def _real_extract(self, url):
        video_id = self._match_id(url)

        try:
            m3u8_url, headers = get_m3u8_url_and_headers(url)
        except M3U8SnifferError as e:
            raise ExtractorError(str(e), expected=True)

        formats = self._extract_m3u8_formats(
            m3u8_url,
            video_id=video_id,
            headers=headers,
            fatal=True,
        )

        episode = None
        m = re.search(r"episode-(\d+)", video_id)
        if m:
            episode = int(m.group(1))

        return {
            "id": video_id,
            "title": video_id.replace("-", " ").title(),
            "episode": episode,
            "formats": formats,
            "http_headers": headers,
        }
