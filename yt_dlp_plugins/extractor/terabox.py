import random
import re
import time
import urllib.parse

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import ExtractorError


class TeraBoxIE(InfoExtractor):
    IE_NAME = 'terabox'
    IE_DESC = 'Terabox shared files (terabox.com / 1024tera.com family)'

    # Matches /s/<id>, /v/<id>, /w/<id> and ?surl=<id> / &surl=<id> on any
    # terabox-family domain. Internal dm.1024tera.com filelist URLs match too.
    _VALID_URL = (
        r'https?://[^/]*(?:terabox|1024tera|mirrobox|nephobox|4funbox|teraboxapp)[^/]*'
        r'(?:/[^?#\s]*[?&#]surl=[^&#/?\s]+|/(?:s|v|w)/[^/?#&]+)'
    )

    _API_BASE = 'https://dm.1024tera.com'
    _APP_ID = '250528'
    _JSTOKEN_RE = r'fn%28%22([0-9A-Fa-f]+)%22%29'
    _CHUNK_IDX_RE = re.compile(r'_(\d+)_ts/')

    # How many playlist polls per quality when discovering HLS chunks.
    # The streaming endpoint returns a RANDOM subset per call, so we poll
    # until the chunk set looks complete (contiguous + quiet streak).
    _MAX_DISCOVERY_REQUESTS = 60
    _DISCOVERY_QUIET_STREAK = 10

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _logid():
        return str(random.randint(400_000_000_000_000_000, 999_999_999_999_999_999))

    def _extract_surl(self, url):
        m = re.search(r'[?&#]surl=([^&#/?\s]+)', url)
        if m:
            return m.group(1)
        m = re.search(r'/(?:s|v|w)/([^/?#&]+)', url)
        if m:
            return m.group(1)
        raise ExtractorError(f'Cannot extract surl from URL: {url!r}', expected=True)

    def _streaming_url(self, shareid, uk, sign, timestamp, fs_id, quality):
        return self._API_BASE + '/share/streaming?' + urllib.parse.urlencode({
            'uk': str(uk), 'shareid': str(shareid), 'type': quality,
            'fid': str(fs_id), 'sign': sign, 'timestamp': str(timestamp),
            'esl': '1', 'isplayer': '1', 'ehps': '1', 'clienttype': '0',
            'app_id': self._APP_ID, 'web': '1', 'channel': 'dubox',
            'dp-logid': self._logid(),
        })

    def _parse_playlist_text(self, text):
        """One streaming response -> [(chunk_idx, seg_url_with_range, size)]."""
        text = (text or '').strip()
        if not text.startswith('#EXTM3U'):
            return []
        out = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parsed = urllib.parse.urlparse(line)
            q = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            try:
                ts_size = int((q.get('ts_size') or ['0'])[0])
            except ValueError:
                continue
            if ts_size <= 0:
                continue
            m = self._CHUNK_IDX_RE.search(parsed.path)
            if not m:
                continue
            q['range'] = [f'0-{ts_size - 1}']
            q['len'] = [str(ts_size)]
            full = urllib.parse.urlunparse(parsed._replace(
                query=urllib.parse.urlencode({k: v[0] for k, v in q.items()})))
            out.append((int(m.group(1)), full, ts_size))
        return out

    def _query_playlist(self, shareid, uk, sign, timestamp, fs_id, quality, surl, referer):
        url = self._streaming_url(shareid, uk, sign, timestamp, fs_id, quality)
        try:
            text = self._download_webpage(
                url, surl, note=False, errnote=False, fatal=False,
                headers={'Referer': referer})
        except ExtractorError:
            return []
        if not text:
            return []
        return self._parse_playlist_text(text)

    def _discover_chunks(self, shareid, uk, sign, timestamp, fs_id, quality, surl, referer):
        known = {}
        reqs = 0
        no_new_streak = 0
        max_idx = -1
        max_requests = self._MAX_DISCOVERY_REQUESTS
        while True:
            reqs += 1
            for item in self._query_playlist(
                    shareid, uk, sign, timestamp, fs_id, quality, surl, referer):
                known.setdefault(item[0], item)
            cur_max = max(known) if known else -1
            if cur_max > max_idx:
                max_idx, no_new_streak = cur_max, 0
            else:
                no_new_streak += 1

            if known and min(known) <= 1 and len(known) == max(known) - min(known) + 1:
                if no_new_streak >= self._DISCOVERY_QUIET_STREAK:
                    break
            budget = min(max_requests, max(30, max_idx * 3)) if max_idx > 0 else 30
            if reqs >= budget:
                break
            time.sleep(random.uniform(0.1, 0.25))
        if not known:
            return []
        return [known[i] for i in sorted(known)]

    @staticmethod
    def _build_manifest(chunks):
        lines = ['#EXTM3U', '#EXT-X-VERSION:3',
                 '#EXT-X-MEDIA-SEQUENCE:0', '#EXT-X-TARGETDURATION:30']
        for _idx, seg_url, _size in chunks:
            lines.append('#EXTINF:10.0,')
            lines.append(seg_url)
        lines.append('#EXT-X-ENDLIST')
        return '\n'.join(lines) + '\n'

    def _try_dlink(self, surl, js_token, shareid, uk, sign, timestamp, fs_id, randsk, referer):
        """POST /share/download -> original-file dlink or None.

        Needs the `ndus` login cookie (user passes --cookies / --cookies-from-browser);
        without it the API returns an error errno and we return None.
        """
        query = {
            'app_id': self._APP_ID, 'web': '1', 'channel': 'dubox',
            'clienttype': '0', 'jsToken': js_token, 'dp-logid': self._logid(),
        }
        post_data = urllib.parse.urlencode({
            'fid_list': f'[{fs_id}]',
            'sekey': urllib.parse.unquote(randsk or ''),
            'uk': uk, 'shareid': shareid, 'sign': sign, 'timestamp': timestamp,
        }).encode()
        try:
            resp = self._download_json(
                self._API_BASE + '/share/download', surl,
                note=False, errnote=False, fatal=False,
                headers={'Referer': referer,
                         'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'},
                query=query, data=post_data)
        except ExtractorError:
            return None
        if not isinstance(resp, dict) or resp.get('errno') != 0 or not resp.get('dlink'):
            return None
        return resp['dlink']

    def _extract_file_entry(self, f, share_ctx):
        surl = share_ctx['surl']
        referer = share_ctx['referer']
        js_token = share_ctx['js_token']
        shareid = share_ctx['shareid']
        uk = share_ctx['uk']
        sign = share_ctx['sign']
        timestamp = share_ctx['timestamp']
        randsk = share_ctx.get('randsk', '')

        fs_id = str(f.get('fs_id'))
        name = f.get('server_filename') or fs_id
        size = self._safe_int(f.get('size'), None)
        is_video = str(f.get('category')) == '1'
        title, dot, ext = name.rpartition('.')
        if not dot:
            title, ext = name, None

        formats = []

        # Original file via login-cookie dlink (best quality, any file type).
        dlink = self._try_dlink(surl, js_token, shareid, uk, sign, timestamp,
                                fs_id, randsk, referer)
        if dlink:
            fmt = {
                'format_id': 'original',
                'url': dlink,
                'quality': 10,
                'http_headers': {'Referer': referer},
            }
            if ext:
                fmt['ext'] = ext.lower()
            if size:
                fmt['filesize'] = size
            formats.append(fmt)

        # HLS for videos (360p/480p, no login needed).
        if is_video:
            for qlabel, height in (('M3U8_AUTO_480', 480), ('M3U8_AUTO_360', 360)):
                probe = self._query_playlist(shareid, uk, sign, timestamp,
                                             fs_id, qlabel, surl, referer)
                if not probe:
                    continue
                self.to_screen(f'{fs_id}: discovering {qlabel} chunks...')
                chunks = self._discover_chunks(shareid, uk, sign, timestamp,
                                               fs_id, qlabel, surl, referer)
                if not chunks:
                    continue
                lo, hi = min(c[0] for c in chunks), max(c[0] for c in chunks)
                if len(chunks) != hi - lo + 1:
                    self.to_screen(
                        f'{fs_id}: {qlabel} partial ({len(chunks)}/{hi - lo + 1} chunks)')
                else:
                    self.to_screen(f'{fs_id}: {qlabel} complete ({len(chunks)} chunks)')
                manifest = self._build_manifest(chunks)
                formats.append({
                    'format_id': f'hls-{height}p',
                    'url': self._streaming_url(shareid, uk, sign, timestamp, fs_id, qlabel),
                    'hls_media_playlist_data': manifest,
                    'protocol': 'm3u8_native',
                    'ext': 'mp4',
                    'height': height,
                    'quality': height,
                    'http_headers': {'Referer': referer},
                })

        if not formats:
            if not is_video:
                self.to_screen(
                    f'{fs_id} ({name}): only original quality is available; '
                    'log into terabox.com and pass --cookies/--cookies-from-browser '
                    'to download it.', only_once=False)
                return None
            raise ExtractorError(
                f'{fs_id} ({name}): no stream available (720p/1080p are premium-gated; '
                'for the original file use a login cookie)')

        info = {
            'id': fs_id,
            'title': title,
            'formats': sorted(formats, key=lambda x: (x.get('quality') or 0, x.get('format_id') or '')),
        }
        if ext:
            info['ext'] = ext.lower()
        # Only advertise the API-reported size when the original file is
        # available (HLS renditions are smaller transcodes).
        if size and dlink:
            info['filesize'] = size
        return info

    @staticmethod
    def _safe_int(v, default=None):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    # -- main ----------------------------------------------------------------

    def _real_extract(self, url):
        surl = self._extract_surl(url)
        referer = f'{self._API_BASE}/wap/share/filelist?surl={surl}'

        webpage = self._download_webpage(
            f'{self._API_BASE}/wap/share/filelist?surl={surl}&clearCache=1',
            surl, headers={'Referer': referer})
        js_token = self._search_regex(self._JSTOKEN_RE, webpage, 'jsToken')

        info = self._download_json(
            self._API_BASE + '/api/shorturlinfo', surl,
            query={'app_id': self._APP_ID, 'shorturl': '1' + surl, 'root': '1',
                   'web': '1', 'channel': 'dubox', 'clienttype': '0',
                   'jsToken': js_token, 't': str(int(time.time())),
                   'dp-logid': self._logid()},
            headers={'Referer': referer,
                     'Accept': 'application/json, text/plain, */*',
                     'Origin': self._API_BASE})

        if not isinstance(info, dict) or info.get('errno') != 0:
            raise ExtractorError(
                f'shorturlinfo failed errno={info.get("errno") if isinstance(info, dict) else "?"} '
                f'msg={((info.get("show_msg") or info.get("errmsg") or "") if isinstance(info, dict) else "")!r} '
                '(link expired/private?)')

        files = info.get('list') or []
        if not files:
            raise ExtractorError('No files in share', expected=True)

        share_ctx = {
            'surl': surl, 'referer': referer, 'js_token': js_token,
            'shareid': info['shareid'], 'uk': info['uk'],
            'sign': info['sign'], 'timestamp': info['timestamp'],
            'randsk': info.get('randsk', ''),
        }

        entries = []
        for f in files:
            try:
                entry = self._extract_file_entry(f, share_ctx)
            except ExtractorError as e:
                self.to_screen(f'skipping {f.get("server_filename")}: {e}')
                continue
            if entry:
                entries.append(entry)

        if not entries:
            raise ExtractorError(
                'No downloadable files (non-video files need a Terabox login cookie: '
                '--cookies "ndus=..." or --cookies-from-browser)', expected=True)

        if len(entries) == 1:
            return entries[0]
        return {
            '_type': 'playlist',
            'id': surl,
            'title': f'Terabox share {surl}',
            'entries': entries,
        }
