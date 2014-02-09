# -*- coding: utf-8 -*-

from __future__ import print_function

import json
import sys
import pickle
import time

from subprocess import call as sub_call
from collections import deque
from importlib import import_module

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

def uopen(url, retries=3, timeout=7):
    data = None
    while retries >= 0:
        try:
            data = url_opener.open(url, timeout=timeout).read().decode("utf8")
        except HTTPError:
            time.sleep(1)
            retries -= 1
        else:
            break
    return data


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
    def __init__(self):
        self.results = []
        self.more_results = True
        self.query = None

    def __chpage(self, incr):
        self.query["page"] += incr

    def search(self, query=None):
        if self.query == None and query == None:
            return
        q = query or self.query
        data = uopen(self.search_url % q)
        self.parse_results(data)
        self.query = q

    def change_page(self, incr):
        if self.query == None or incr == 0:
            return
        elif incr > 0:
            if not self.more_results:
                return
        else:
            if self.query["page"] == 1:
                return
        self.__chpage(incr)
        self.search()

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
        
    def __chpage(self, incr):
        self.query["page"] += incr
        page = self.query["page"]
        per_page = self.query["max_res"]
        self.query["start_res"] = 1 + (per_page * (page-1))


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
        jdata = uopen(fetch_url)
        jobj = json.loads(jdata)
        if "track_link" in jobj:
            return jobj["track_link"]
        else:
            return None


class Playlist(object):

    def __init__(self, n, queue=None):
        self.name = n
        self.queue = queue

    def add(self, item, before=False):
        if before:
            self.queue.insert(0, item)
        else:
            self.queue.append(item)

    def remove(self, idx):
        del self.queue[idx]

    def save(self, fh):
        pickle.dump(self, fh, protocol=2)

    @classmethod
    def load(cls, fh):
        plist = pickle.load(fh)
        return cls(plist.name, plist.queue)


class MpvBackend(object):

    def __init__(self):
        self.__cmd  = "mpv"
        self.__args = ["--really-quiet", "--no-lirc", "--no-cache"]
        self.__vid  = True

    def play_url(self, url):
        cmd = [__cmd] + __args
        if not __vid:
            cmd += ["--no-video"]
        cmd += url
        sub_call(cmd) 

    def toggle_video(self):
        self.__vid = not self.__vid


class Player(object):
    
    def __init__(self, backend=None):
        self.__pl = Playlist("Default")
        self.__state = 0
        self.__flags = {"shuffle":False, "repeat":False}
        self.__back  = backend or MpvBackend()
        self.__get_searches()
        self.__track = -1
        
    def __get_searches(self):
        self.__searches = [cls() for cls in Search.__subclasses__()]

    def queue_playlist(self, pf, autoplay=False):
        self.__pl = Playlist.load(pf)
        if autoplay:
            self.play()

    def play(self):
        self.__state = 1
        for i,item in enumerate(self.__pl.queue):
            url = item.resolve_url()
            self.__track = i
            self.__back.play_url(url)

    def search(self, text, nres=5, engines=None):
        if text == "":
            return [s.results for s in self.__searches]

        query = {
            "page":1,
            "max_res":nres,
            "start_res":1,
            "terms":text
            }
        for s in self.__searches:
            s.search(query)
        return [s.results for s in self.__searches]

    def search_change_page(self, incr=1):
        for s in self.__searches:
            s.change_page(incr)
        return [s.results for s in self.__searches]

    @property
    def state(self):
        state_map = {
                0 : "Stopped",
                1 : "Playing",
                }
        return (self.__state, state_map[self.__state])

    @property
    def playlist(self):
        return self.__pl
