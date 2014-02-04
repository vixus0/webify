#!/usr/bin/env python

from __future__ import print_function

import json
import sys
import pickle
import time

if sys.version_info[0] > 2:
    from urllib.request import build_opener, HTTPSHandler
    from urllib.error import HTTPError, URLError
    from html.parser import HTMLParser, HTMLParseError
else:
    from urllib2 import build_opener, HTTPSHandler, HTTPError, URLError
    from HTMLParser import HTMLParser, HTMLParseError

user_agent = "Mozilla/5.0"
url_opener = build_opener(HTTPSHandler)
url_opener.addheaders = [("User-Agent", user_agent)]
uopen = url_opener.open


class Result(object):
    def __init__(self, title, link, source):
        self.title = title
        self.link = link
        self.source = source

    def resolve_url(self):
        return self.source.resolve_url(self)

    def __repr__(self):
        return "Result( %(title)s, %(link)s, %(source)s )" % self.__dict__


class Search(object):
    retry = 3

    def __init__(self):
        self.results = []
        self.page = 0
        self.more_results = True

    def search(self, query):
        lives = self.retry
        while lives >= 0:
            try:
                data = uopen(self.search_url % query, timeout=7).read().decode("utf8")
            except HTTPError:
                time.sleep(1)
                lives -= 1
            else:
                break
        self.parse_results(data)
        self.page = query["page"]

    def resolve_url(self, result):
        return self.stream_url % result.link
            
    def __repr__(self):
        return self.slug


class DailymotionSearch(Search):
    slug = "dm"
    search_url = "https://api.dailymotion.com/videos?sort=relevance&page=%(page)d&limit=%(max_res)d&search=%(terms)s"
    stream_url = "http://www.dailymotion.com/video/%s"

    def parse_results(self, data):
        jobj = json.loads(data)
        if jobj["total"] > 0:
            self.results = [Result(
                item["title"],
                item["id"],
                self
                ) for item in jobj["list"]]

        self.more_results = jobj["has_more"]


class YoutubeSearch(Search):
    slug = "yt"
    search_url = "http://gdata.youtube.com/feeds/api/videos?v=2&max-results=%(max_res)d&start-index=%(start_res)d&alt=json&q=%(terms)s"
    stream_url = "http://www.youtube.com/v/%s"

    def parse_results(self, data):
        jobj = json.loads(data)
        if "entry" in jobj["feed"]:
            self.results = [Result(
                item["title"]["$t"],
                item["id"]["$t"].split("/")[-1],
                self
                ) for item in jobj["feed"]["entry"]]

        start_index = jobj["feed"]["openSearch$startIndex"]["$t"]
        total_res   = jobj["feed"]["openSearch$totalResults"]["$t"]
        per_page    = jobj["feed"]["openSearch$itemsPerPage"]["$t"]

        self.more_results = start_index < total_res - per_page


class PleerSearch(Search, HTMLParser):
    slug = "pleer"
    search_url = "http://pleer.com/search?q=%(terms)s&target=tracks&page=%(page)d"
    stream_url = "http://pleer.com/site_api/files/get_url?action=download&id=%s"

    def __init__(self):
        self.li = [] 
        Search.__init__(self)
        HTMLParser.__init__(self)

    def parse_results(self, data):
        self.feed(data)
        self.results = [Result(
            item["singer"]+" | "+item["song"],
            item["link"],
            self
            ) for item in self.li]

    def handle_starttag(self, tag, attrs):
        if tag != "li":
            return

        adict = {}
        for k,v in attrs:
            adict[k] = v

        if "duration" not in adict.keys():
            return

        self.li.append(adict)

    def resolve_url(self, result):
        fetch_url = self.stream_url % result.link

        print("Fetching: "+fetch_url)

        lives = self.retry
        while lives >= 0:
            try:
                jdata = uopen(fetch_url, timeout=7).read().decode("utf8")
            except HTTPError:
                time.sleep(1)
                lives -= 1
            else:
                break

        if lives < 0:
            return None

        jobj = json.loads(jdata)
        if "track_link" in jobj:
            return jobj["track_link"]
        else:
            return None
        

def test_searches(query):
    for cls in [DailymotionSearch, YoutubeSearch, PleerSearch]:

        test_search = {
            "page":1, 
            "max_res":5,
            "start_res":1,
            "terms":query
            }

        s = cls()

        print(s)
        s.search(test_search)
        print(s.results)
        print("\n\n")

        print(s.results[0].resolve_url())
        print("\n\n\n")