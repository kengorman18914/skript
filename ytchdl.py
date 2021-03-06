#!/usr/bin/env python3
'''
Created on 27 October 2012

@author: Anton Eliasson <devel@antoneliasson.se>

Planned features:
* Split the url_file into two files. One M3U url_file containing only the filenames
  for the user and a hidden url_file containing the URLs for the script. The url_file can
  then be modified freely by the user without affecting the scripts ability to update.
* Add an update option which takes no other arguments but rather reads the channel
  name from the hidden url_file.

Known bugs and limitations:
* youtube-dl might take the initiative to download the MP4 version if there's no WebM version available.

Changelog:
1. First stable version. Stores downloaded URLs in the url_file url_file.

'''

import logging
import subprocess
from optparse import OptionParser

import feedparser

def get_feed_links(channel, skip):
    base_url = "http://gdata.youtube.com/feeds/api/users/%s/uploads" % channel
    logging.debug("Using feed URL: %s " % base_url)
    index = 1
    downloads = []
    page_url = base_url + "?start-index=" + str(index) + "&max-results=50"
    feed = feedparser.parse(page_url)
    if feed.status == 200:
        logging.debug("Found channel %s" % feed.feed.author)
        while (feed.entries):
            for entry in feed.entries:
                # strip extra URL parameters
                link = entry.link[:-22]
                if link in skip:
                    logging.debug("Skipping URL %s published %s" % (link, entry.published))
                else:
                    logging.info("Adding URL %s published %s" % (link, entry.published))
                    downloads.append(link)
            # Get next page
            index += 50
            page_url = base_url + "?start-index=" + str(index) + "&max-results=50"
            feed = feedparser.parse(page_url)
        
        # Entries are by default ordered by the date published, in reverse chronological order.
        # (https://developers.google.com/youtube/2.0/developers_guide_protocol_api_query_parameters#orderbysp)
        # Now reverse the list so that it's ordered from oldest to newest.
        downloads.reverse()
    return (feed.status, downloads)

def download(downloads):
    filenames = []
    for url in downloads:
        logging.info("Downloading %s" % url)
        # TODO: add non-free MP4 as option
        program = 'youtube-dl'
        args = ['--prefer-free-formats', '-o', '%(title)s.%(ext)s']
        cmd = [program] + args + [url]
        try:
            output = subprocess.check_output(cmd).decode()
            lines = output.split('\n')
            filename = lines[4][24:]
            filenames.append(filename)
        except OSError as e:
            logging.error("Could not execute %s: %s" % (program, e.strerror))
    return filenames

def import_urls(filename):
    urls = []
    # FIXME: change the try block to a with block
    try:
        url_file = open(filename)
    except FileNotFoundError:
        return urls
    
    # throw away the beginning comments
    url_file.readline()
    url_file.readline()
    
    line = url_file.readline()
    while line:
        urls.append(line.strip())
        line = url_file.readline()
    url_file.close()
    return urls

def export_playlist(playlist, filenames):
    # FIXME: put this in a try/with block
    playlist_file = open(playlist, 'a')
    
    for filename in filenames:
        print(filename)
        playlist_file.write(filename + '\n')
    playlist_file.close()

def export_urls(filename, urls):
    # FIXME: put this in a try/with block
    url_file = open(filename, 'w')
    
    url_file.write('List of downloaded URLs by ytchdl.\n'
    'Do not edit unless you know what you are doing.\n')
    
    for url in urls:
        url_file.write(url + '\n')
    url_file.close()

if __name__ == "__main__":
    parser = OptionParser(
            usage="%prog [options] channel",
            version="%prog 0.1")
    parser.add_option("-p","--url_file",
            dest="playlist",
            default="",
            action="store",
            help="M3U url_file to use. Defaults to <channel>.m3u")
    parser.add_option("-u","--urls-only",
            dest="urls_only",
            default=False,
            action="store_true",
            help="Only print the links to all videos in the channel without downloading anything")
    parser.add_option("-v","--verbose",
            dest="verbose",
            default=False,
            action="store_true",
            help="Be more verbose")
    (options,args) = parser.parse_args()
    
    verbose = options.verbose
    urls_only = options.urls_only
    
    # TODO: add debug mode
    if verbose:
        logging.basicConfig(format='%(levelname)s %(message)s', level=logging.INFO)
    else:
        logging.basicConfig(format='%(levelname)s %(message)s', level=logging.WARNING)
    
    if len(args) == 0:
        parser.error("No YouTube channel specified")
    channel = args[0].lower()
    
    if options.playlist:
        playlist_file = options.playlist
        # FIXME: fail if specified url_file url_file does not exist
    else:
        playlist_file = channel + '.m3u'
    
    url_file = '.ytchdl'
    skip = import_urls(url_file)
    
    (status, downloads) = get_feed_links(channel, skip)
    if status == 200:
        if urls_only:
            print('New URLs:')
            for url in downloads:
                print(url)
        else:
            filenames = download(downloads)
            export_playlist(playlist_file, filenames)
            export_urls(url_file, skip + downloads)
    elif status == 404:
        logging.error('Channel %s not found' % channel)
    else:
        logging.error('Unknown status code from API: %d' % status)
    
