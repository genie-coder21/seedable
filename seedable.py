#!/usr/bin/env python3

import os
import re
import logging
import hashlib
import time
from typing import List, Dict, Any, Tuple
from collections import defaultdict
from datetime import datetime
from flask import Flask, request, Response
import requests
from xml.etree.ElementTree import Element, SubElement, tostring

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('seedable')

NZBHYDRA_URL = os.getenv('NZBHYDRA_URL', 'http://YOUR_SERVER_IP:5076')
NZBHYDRA_API_KEY = os.getenv('NZBHYDRA_API_KEY', '')
API_KEY = os.getenv('API_KEY', 'seedable-default-key')
MIN_DUPLICATES = int(os.getenv('MIN_DUPLICATES', '2'))
SIZE_TOLERANCE_PERCENT = float(os.getenv('SIZE_TOLERANCE_PERCENT', '2.0'))
PORT = int(os.getenv('PORT', '5000'))
HOST = os.getenv('HOST', '0.0.0.0')

RADARR_URL = os.getenv('RADARR_URL', 'http://YOUR_SERVER_IP:7878')
RADARR_API_KEY = os.getenv('RADARR_API_KEY', '')
SONARR_URL = os.getenv('SONARR_URL', 'http://YOUR_SERVER_IP:8989')
SONARR_API_KEY = os.getenv('SONARR_API_KEY', '')

PRIVATE_TRACKERS_STR = os.getenv('PRIVATE_TRACKERS', '')
PRIVATE_TRACKERS = set(t.strip() for t in PRIVATE_TRACKERS_STR.split(',') if t.strip())

app = Flask(__name__)

results_cache = {}
CACHE_TTL = 60


def get_cache_key(params: Dict[str, str]) -> str:
    cache_params = {
        'q': params.get('q', ''),
        'cat': params.get('cat', ''),
        'imdbid': params.get('imdbid', ''),
        'tvdbid': params.get('tvdbid', ''),
        'season': params.get('season', ''),
        'ep': params.get('ep', ''),
        't': params.get('t', ''),
    }
    key_str = str(sorted(cache_params.items()))
    return hashlib.md5(key_str.encode()).hexdigest()


def clean_expired_cache():
    current_time = time.time()
    expired_keys = [k for k, v in results_cache.items()
                    if current_time - v['timestamp'] > CACHE_TTL]
    for key in expired_keys:
        del results_cache[key]
        logger.debug(f"Removed expired cache entry: {key}")


def normalize_title(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r'[._-]+', ' ', normalized)
    normalized = re.sub(r'\bwww\s+\w+\s+(org|com|net)\b', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized.strip()


def format_rfc822_date(date_str: str) -> str:
    if not date_str:
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')

    try:
        if 'T' in date_str:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        elif '-' in date_str and ' ' in date_str:
            dt = datetime.strptime(date_str, '%d-%m-%Y %H:%M')
        else:
            dt = datetime.utcnow()
    except (ValueError, AttributeError):
        dt = datetime.utcnow()

    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')


def get_size_bucket(size_bytes: int, tolerance_percent: float = SIZE_TOLERANCE_PERCENT) -> int:
    size_mb = size_bytes / (1024 * 1024)

    if size_mb < 100:
        bucket_size = 10
    elif size_mb < 1000:
        bucket_size = 50
    else:
        bucket_size = 100

    return round(size_mb / bucket_size) * bucket_size


def group_results(results: List[Dict[str, Any]]) -> Dict[Tuple, List[Dict[str, Any]]]:
    groups = defaultdict(list)

    for result in results:
        title = result.get('title', '')
        size = result.get('size', 0)

        norm_title = normalize_title(title)
        size_bucket = get_size_bucket(size)

        key = (norm_title, size_bucket)
        groups[key].append(result)

    return groups


def filter_cross_seedable(groups: Dict[Tuple, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    cross_seedable = []

    for group_key, group_results in groups.items():
        if len(group_results) < MIN_DUPLICATES:
            logger.debug(f"Group '{group_key[0][:50]}...' has {len(group_results)} matches - FILTERED (below min)")
            continue

        private_count = 0
        public_count = 0

        for result in group_results:
            indexer = result.get('indexer', '')
            if indexer in PRIVATE_TRACKERS:
                private_count += 1
            else:
                public_count += 1

        if PRIVATE_TRACKERS and private_count == 0:
            logger.debug(f"Group '{group_key[0][:50]}...' has only public trackers ({public_count} public) - FILTERED")
            continue

        for result in group_results:
            result['_tracker_counts'] = {
                'private': private_count,
                'public': public_count
            }
            cross_seedable.append(result)

        if PRIVATE_TRACKERS:
            logger.debug(f"Group '{group_key[0][:50]}...' - KEPT ({private_count} private, {public_count} public)")
        else:
            logger.debug(f"Group '{group_key[0][:50]}...' has {len(group_results)} matches - KEPT")

    return cross_seedable


def lookup_title_from_radarr(imdb_id: str) -> str:
    if not RADARR_URL or not RADARR_API_KEY:
        return ''

    try:
        if not imdb_id.startswith('tt'):
            imdb_id = f'tt{imdb_id}'

        url = f"{RADARR_URL}/api/v3/movie/lookup/imdb"
        params = {'imdbId': imdb_id}
        headers = {'X-Api-Key': RADARR_API_KEY}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and data.get('title'):
            title = data['title']
            logger.info(f"Looked up IMDb {imdb_id} via Radarr → title: '{title}'")
            return title

        logger.warning(f"No title found for IMDb ID {imdb_id} in Radarr")
        return ''

    except requests.exceptions.RequestException as e:
        logger.error(f"Error looking up IMDb ID {imdb_id} from Radarr: {e}")
        return ''


def lookup_title_from_sonarr(tvdb_id: str) -> str:
    if not SONARR_URL or not SONARR_API_KEY:
        return ''

    try:
        url = f"{SONARR_URL}/api/v3/series/lookup"
        params = {'term': f'tvdb:{tvdb_id}'}
        headers = {'X-Api-Key': SONARR_API_KEY}

        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0 and data[0].get('title'):
            title = data[0]['title']
            logger.info(f"Looked up TVDb {tvdb_id} via Sonarr → title: '{title}'")
            return title

        logger.warning(f"No title found for TVDb ID {tvdb_id} in Sonarr")
        return ''

    except requests.exceptions.RequestException as e:
        logger.error(f"Error looking up TVDb ID {tvdb_id} from Sonarr: {e}")
        return ''


def query_nzbhydra(params: Dict[str, str]) -> Dict[str, Any]:
    category_map = {
        '2000': 'Movies',
        '2010': 'Movies SD',
        '2040': 'Movies HD',
        '2045': 'Movies UHD',
        '5000': 'TV',
        '5030': 'TV SD',
        '5040': 'TV HD',
        '5045': 'TV UHD',
    }

    query = params.get('q', '')

    if not query:
        if params.get('imdbid'):
            looked_up_title = lookup_title_from_radarr(params.get('imdbid'))
            if looked_up_title:
                query = looked_up_title
                logger.info(f"Using Radarr lookup: '{query}' instead of just IMDb ID")
        elif params.get('tvdbid'):
            looked_up_title = lookup_title_from_sonarr(params.get('tvdbid'))
            if looked_up_title:
                query = looked_up_title
                logger.info(f"Using Sonarr lookup: '{query}' instead of just TVDb ID")

    hydra_params = {
        'query': query,
        'category': category_map.get(params.get('cat', ''), 'All'),
    }

    if params.get('season'):
        hydra_params['season'] = params.get('season')
    if params.get('ep'):
        hydra_params['episode'] = params.get('ep')

    if params.get('imdbid'):
        imdb = params.get('imdbid')
        if not imdb.startswith('tt'):
            imdb = f'tt{imdb}'
        hydra_params['imdbid'] = imdb
    if params.get('tvdbid'):
        hydra_params['tvdbid'] = params.get('tvdbid')

    logger.info(f"Querying NZBHydra2: {hydra_params}")

    try:
        url = f"{NZBHYDRA_URL}/internalapi/search"

        params = {}
        if NZBHYDRA_API_KEY:
            params['apikey'] = NZBHYDRA_API_KEY

        response = requests.post(url, json=hydra_params, params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error querying NZBHydra2: {e}")
        return {'searchResults': [], 'numberOfAvailableResults': 0}


def map_category_to_torznab(category: str) -> str:
    category_mapping = {
        'movies': '2000',
        'movies foreign': '2010',
        'movies other': '2020',
        'movies sd': '2030',
        'movies hd': '2040',
        'movies uhd': '2045',
        'movies 4k': '2045',
        'movies bluray': '2050',
        'movies 3d': '2060',
        'tv': '5000',
        'tv foreign': '5020',
        'tv sd': '5030',
        'tv hd': '5040',
        'tv uhd': '5045',
        'tv 4k': '5045',
        'tv other': '5050',
        'tv sport': '5060',
        'tv anime': '5070',
        'anime': '5070',
        'tv documentary': '5080',
        'audio': '3000',
        'audio mp3': '3010',
        'audio video': '3020',
        'audio audiobook': '3030',
        'audio lossless': '3040',
        'console': '1000',
        'pc': '4000',
        'xxx': '6000',
        'books': '7000',
        'other': '8000',
    }

    cat_lower = category.lower().strip()
    return category_mapping.get(cat_lower, '2000')


def results_to_torznab_xml(results: List[Dict[str, Any]]) -> str:
    rss = Element('rss', version='2.0')
    rss.set('xmlns:torznab', 'http://torznab.com/schemas/2015/feed')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')

    channel = SubElement(rss, 'channel')

    SubElement(channel, 'title').text = 'Seedable - Cross-Seed Filter'
    SubElement(channel, 'description').text = 'Filtered torrents available on 2+ trackers'
    SubElement(channel, 'link').text = request.url_root

    logger.info(f"Building XML for {len(results)} results")

    for idx, result in enumerate(results):
        item = SubElement(channel, 'item')

        title = result.get('title', 'Unknown')

        if '_tracker_counts' in result and PRIVATE_TRACKERS:
            counts = result['_tracker_counts']
            private_count = counts['private']
            public_count = counts['public']
            title = f"[PRI:{private_count} PUB:{public_count}] {title}"

        SubElement(item, 'title').text = title
        SubElement(item, 'guid').text = result.get('searchResultId', str(idx))

        link = result.get('link', '')
        if not link:
            logger.warning(f"Result '{title}' has no download link!")

        SubElement(item, 'link').text = link

        size = result.get('size', 0)
        SubElement(item, 'enclosure',
                   url=link,
                   length=str(size),
                   type='application/x-bittorrent')

        SubElement(item, 'comments').text = result.get('details_link', '')

        raw_date = result.get('pubDate', result.get('date', ''))
        SubElement(item, 'pubDate').text = format_rfc822_date(raw_date)

        SubElement(item, 'size').text = str(size)
        SubElement(item, 'description').text = f"Tracker: {result.get('indexer', 'Unknown')}"

        category = result.get('category', 'Movies')
        category_id = map_category_to_torznab(category)

        SubElement(item, 'category').text = category_id

        SubElement(item, 'torznab:attr', name='size', value=str(size))
        SubElement(item, 'torznab:attr', name='category', value=category_id)

        seeders = result.get('seeders', 0)
        peers = result.get('peers', 0)
        SubElement(item, 'torznab:attr', name='seeders', value=str(seeders))
        SubElement(item, 'torznab:attr', name='peers', value=str(peers))

        SubElement(item, 'torznab:attr', name='grabs', value=str(result.get('grabs', 0)))
        SubElement(item, 'torznab:attr', name='downloadvolumefactor',
                   value='0' if result.get('downloadVolumeFactor', result.get('torrentDownloadFactor')) == 'Freelech' else '1')
        SubElement(item, 'torznab:attr', name='uploadvolumefactor', value='1')

        SubElement(item, 'torznab:attr', name='indexer', value=result.get('indexer', 'Unknown'))

        if idx == 0:
            logger.info(f"First result: title='{title[:50]}', category={category_id}, size={size}, link={'present' if link else 'MISSING'}")

    xml_string = tostring(rss, encoding='unicode', method='xml')
    final_xml = f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}'

    logger.info(f"Generated XML with {len(results)} items, {len(final_xml)} bytes")

    return final_xml


@app.route('/api')
def torznab_api():
    params = request.args.to_dict()

    logger.info(f"=== INCOMING REQUEST ===")
    logger.info(f"Request type: {params.get('t', 'unknown')}")
    logger.info(f"Full params: {params}")
    logger.info(f"User-Agent: {request.headers.get('User-Agent', 'unknown')}")

    if params.get('apikey') != API_KEY:
        logger.warning(f"Invalid API key: {params.get('apikey')}")
        return Response('Invalid API key', status=403)

    if params.get('t') == 'caps':
        logger.info("Returning capabilities")
        return get_capabilities()

    if params.get('t') in ['search', 'movie', 'tvsearch']:
        logger.info(f"=== SEARCH REQUEST ===")

        clean_expired_cache()

        cache_key = get_cache_key(params)

        if cache_key in results_cache:
            cache_entry = results_cache[cache_key]
            cache_age = time.time() - cache_entry['timestamp']
            if cache_age < CACHE_TTL:
                filtered_results = cache_entry['results']
                logger.info(f"Using cached results (age: {cache_age:.1f}s, {len(filtered_results)} results)")
            else:
                del results_cache[cache_key]
                filtered_results = None
        else:
            filtered_results = None

        if filtered_results is None:
            hydra_response = query_nzbhydra(params)

            all_results = hydra_response.get('searchResults', [])
            logger.info(f"NZBHydra2 returned {len(all_results)} total results")

            requested_imdbid = params.get('imdbid')
            requested_tvdbid = params.get('tvdbid')

            if requested_imdbid:
                if not requested_imdbid.startswith('tt'):
                    requested_imdbid = f'tt{requested_imdbid}'
                all_results = [r for r in all_results if r.get('imdbId') == requested_imdbid]
                logger.info(f"Filtered to {len(all_results)} results matching IMDb ID {requested_imdbid}")

            if requested_tvdbid and not requested_imdbid:
                all_results = [r for r in all_results if str(r.get('tvdbId')) == requested_tvdbid]
                logger.info(f"Filtered to {len(all_results)} results matching TVDb ID {requested_tvdbid}")

            groups = group_results(all_results)
            logger.info(f"Grouped into {len(groups)} unique releases")

            filtered_results = filter_cross_seedable(groups)
            logger.info(f"Filtered to {len(filtered_results)} cross-seedable results (min {MIN_DUPLICATES} trackers)")

            requested_cats = params.get('cat', '').split(',') if params.get('cat') else []
            if requested_cats:
                category_filtered = []
                for result in filtered_results:
                    result_cat = map_category_to_torznab(result.get('category', 'Movies'))
                    if result_cat in requested_cats or result_cat[:1] + '000' in requested_cats:
                        category_filtered.append(result)
                logger.info(f"Category filtered to {len(category_filtered)} results matching {requested_cats}")
                filtered_results = category_filtered

            seen_urls = set()
            unique_results = []
            for result in filtered_results:
                url = result.get('link', '')
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    unique_results.append(result)

            if len(unique_results) < len(filtered_results):
                logger.info(f"Deduplicated {len(filtered_results)} → {len(unique_results)} results (removed {len(filtered_results) - len(unique_results)} duplicate URLs)")
                filtered_results = unique_results

            results_cache[cache_key] = {
                'results': filtered_results,
                'timestamp': time.time()
            }
            logger.info(f"Cached {len(filtered_results)} results (key: {cache_key[:8]}...)")

        offset = int(params.get('offset', 0))
        limit = int(params.get('limit', 100))

        total_results = len(filtered_results)
        paginated_results = filtered_results[offset:offset + limit]

        logger.info(f"Pagination: offset={offset}, limit={limit}, total={total_results}, returning={len(paginated_results)}")

        xml_response = results_to_torznab_xml(paginated_results)

        return Response(xml_response, mimetype='application/xml')

    return Response('Unknown request type', status=400)


def get_capabilities():
    caps = Element('caps')

    server = SubElement(caps, 'server', version='1.0', title='Seedable')

    limits = SubElement(caps, 'limits', max='100', default='100')

    searching = SubElement(caps, 'searching')
    SubElement(searching, 'search', available='yes', supportedParams='q')
    SubElement(searching, 'tv-search', available='yes',
               supportedParams='q,season,ep,tvdbid')
    SubElement(searching, 'movie-search', available='yes',
               supportedParams='q,imdbid')

    categories = SubElement(caps, 'categories')

    movies = SubElement(categories, 'category', id='2000', name='Movies')
    SubElement(movies, 'subcat', id='2010', name='Movies/Foreign')
    SubElement(movies, 'subcat', id='2020', name='Movies/Other')
    SubElement(movies, 'subcat', id='2030', name='Movies/SD')
    SubElement(movies, 'subcat', id='2040', name='Movies/HD')
    SubElement(movies, 'subcat', id='2045', name='Movies/UHD')
    SubElement(movies, 'subcat', id='2050', name='Movies/BluRay')
    SubElement(movies, 'subcat', id='2060', name='Movies/3D')

    tv = SubElement(categories, 'category', id='5000', name='TV')
    SubElement(tv, 'subcat', id='5020', name='TV/Foreign')
    SubElement(tv, 'subcat', id='5030', name='TV/SD')
    SubElement(tv, 'subcat', id='5040', name='TV/HD')
    SubElement(tv, 'subcat', id='5045', name='TV/UHD')
    SubElement(tv, 'subcat', id='5050', name='TV/Other')
    SubElement(tv, 'subcat', id='5060', name='TV/Sport')
    SubElement(tv, 'subcat', id='5070', name='TV/Anime')
    SubElement(tv, 'subcat', id='5080', name='TV/Documentary')

    audio = SubElement(categories, 'category', id='3000', name='Audio')
    SubElement(audio, 'subcat', id='3010', name='Audio/MP3')
    SubElement(audio, 'subcat', id='3020', name='Audio/Video')
    SubElement(audio, 'subcat', id='3030', name='Audio/Audiobook')
    SubElement(audio, 'subcat', id='3040', name='Audio/Lossless')

    SubElement(categories, 'category', id='1000', name='Console')
    SubElement(categories, 'category', id='4000', name='PC')
    SubElement(categories, 'category', id='6000', name='XXX')
    SubElement(categories, 'category', id='7000', name='Books')
    SubElement(categories, 'category', id='8000', name='Other')

    xml_string = tostring(caps, encoding='unicode', method='xml')
    return Response(f'<?xml version="1.0" encoding="UTF-8"?>\n{xml_string}',
                    mimetype='application/xml')


@app.route('/health')
def health():
    return {'status': 'healthy', 'min_duplicates': MIN_DUPLICATES}


@app.route('/')
def index():
    return f"""
    <html>
    <head><title>Seedable</title></head>
    <body>
        <h1>Seedable - Cross-Seed Torznab Filter</h1>
        <p>Status: <strong>Running</strong></p>
        <p>Minimum trackers required: <strong>{MIN_DUPLICATES}</strong></p>
        <p>Size tolerance: <strong>{SIZE_TOLERANCE_PERCENT}%</strong></p>
        <p>NZBHydra2 URL: <strong>{NZBHYDRA_URL}</strong></p>
        <hr>
        <h3>Add to Sonarr/Radarr:</h3>
        <ul>
            <li>URL: <code>{request.url_root}api</code></li>
            <li>API Key: <code>{API_KEY}</code></li>
        </ul>
    </body>
    </html>
    """


if __name__ == '__main__':
    logger.info(f"Starting Seedable on {HOST}:{PORT}")
    logger.info(f"NZBHydra2 URL: {NZBHYDRA_URL}")
    logger.info(f"Minimum duplicates: {MIN_DUPLICATES}")
    logger.info(f"Size tolerance: {SIZE_TOLERANCE_PERCENT}%")
    app.run(host=HOST, port=PORT, debug=False)
