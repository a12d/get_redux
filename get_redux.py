#!/usr/bin/env python3

from httplib2 import Http
from urllib.parse import urlencode
import urllib.request
import json
from pprint import PrettyPrinter
import re
import argparse
import sys
import os.path

def get_config(config_file):
    fin = open(config_file)
    config = json.load(fin)
    return(config)

def get_output_filename(programme_data, media):
    programme_title = ""
    episode_number = ""
    episode_title = ""
    series_title = ""
    filename_extension = ""

    programme_title = re.sub('\s', "_", programme_data['title'])

    if 'episode' in programme_data:
        if 'position' in programme_data['episode']:
            episode_number = programme_data['episode']['position']
        else:
            episode_number = "XX"
        episode_title = re.sub('\s', "_", programme_data['episode']['title'])
    else:
        episode_number = programme_data['uuid']

    if 'series' in programme_data:
        if 'position' in programme_data['series']:
            series_title = "Series_" + str(programme_data['series']['position']).zfill(2)
        else:
            series_title = programme_data['series']['title']
    else:
        series_title = "special"
    
    filename_extension = programme_data['media'][media]['ext']

    output_filename = programme_title 

    if not programme_title == series_title:
        output_filename = output_filename + "_-_" + series_title 
    output_filename = output_filename + "_-_Episode_" + str(episode_number).zfill(2) 

    if not (re.match("^episode_[0-9]", episode_title, flags=re.I) or episode_title is ""):
        output_filename = output_filename +"_-_" + episode_title 

    output_filename = output_filename + "." + filename_extension

    return(output_filename)

def debug_print(data):
    if debug:
        pp = PrettyPrinter(indent=4)
        pp.pprint(data)

def get_show_title_search_url(show):
    search_string = re.sub("\s", "+", show)
    search_url_stub = "http://devapi.bbcredux.com/search.json?limit=256&sort=date&pname="
    search_url = search_url_stub + search_string
    return search_url

def get_full_text_search_url(show):
    search_string = re.sub("\s", "+", show)
    search_url_stub = "http://devapi.bbcredux.com/search.json?limit=256&sort=date&q="
    search_url = search_url_stub + search_string
    return search_url

def get_programmes(search_url, date, channel, series):
    #http = create_http_connection()

    resp, content = http.request(search_url)

    if re.match("^4", resp['status']):
        print("Problem searching " + search_url + " Status: " + resp['status'])
        sys.exit(1)
    else:
        data = json.loads(str(content.decode("utf-8")))

    debug_print(data)
	
    programmes = []
    for programme in data["results"]:
        if date and not (programme["date"] == date):
            continue
        if channel and not (programme["service"] == channel):
            continue
        if series:
            if 'series' in programme and 'position' in programme['series']:
                if not programme['series']['position'] == series:
                    continue
            else:
                continue
        programmes.append(programme["diskref"])

    programmes.reverse() # puts earliest pisode first
    return(programmes)

def create_http_connection():
    http = Http(".cache", timeout=30)
    http.add_credentials(config['username'], config['password'])
    return(http)

def get_programme_details(programme):
    #http = create_http_connection()
    media_url_stub = "http://devapi.bbcredux.com/programme/"
    media_url = media_url_stub + programme + ".json"

    resp, content = http.request(media_url)

    if re.match("^4", resp['status']):
        print("Problem downloading " + media_url + " Status: " + resp['status'])
        sys.exit(1)
    else:
        data = json.loads(str(content.decode("utf-8")))
        return(data)

def list_programme_description(programme):
    data = get_programme_details(programme)
    print(programme + ": " + str(data['episode']))

def get_programme_content(programme):
    data = get_programme_details(programme)
    debug_print(data)
	
    if data['type'] == options.type:
        output_filename = get_output_filename(data, options.media)
	
        media_uri = data['media'][options.media]['uri']
        if not options.debug:
            print(media_uri + " downloading as " + output_filename)
            try:
                if options.quiet:
                    urllib.request.urlretrieve(media_uri, 
                                               output_filename)
                else:
                    urllib.request.urlretrieve(media_uri, \
                                               output_filename, \
                                               reporthook=dlProgress) 
            except:
                print("problem downloading url " + \
                          media_uri + " :" + str(sys.exc_info()[0]))
            print("\nDone\n")
        else:
            print("Meadia URL: " + media_uri)
            print("Filename:   " + output_filename)
            print()

def dlProgress(count, blockSize, totalSize):
    megabyte = 1048576
    percent = int(count*blockSize*100/totalSize)
    sys.stdout.write("\r%2d%%\t\t%.2fMB / %.2fMB" % (percent, count*blockSize/megabyte, totalSize/megabyte))
    sys.stdout.flush()

def config_help():
    print(
        """The config file should consist of a JSON file with a hash
        with the username and password. i.e.

        { 
        "username": "myusername", 
        "password": "mypassword", 
        "default_audio_type": "mp3" 
        "default_video_type": "mp4-hi" 
        }

        This should be in ~/.get_redux.cfg
        """)

def set_media_type(type, config):
    if type == "radio":
        if "default_audio_type" in config:
            return(config["default_audio_type"])
        else:
            return("mp3")
    else:
        if "default_video_type" in config:
            return(config["default_video_type"])
        else:
            return("mp4-hi")

def main():
    default_config_file = os.path.expanduser('~/.get_redux.cfg')
    parser = argparse.ArgumentParser('Download all shows with a show name matching a particular pattern')
    parser.add_argument('-s', '--show', dest="show", 
                        help="name of the show to be downloaded")
    parser.add_argument('-f', '--full-text', dest="full_text", 
                        help="full text search to be downloaded")
    parser.add_argument('-m', '--media', dest="media", default=False, 
                        help="type of file to be downloaded, e.g. mp3, mp4-hi")
    parser.add_argument('-t', '--type', dest="type", default="tv",
                        help="type of show. 'tv' or 'radio'")
    parser.add_argument("-z", "--date", dest="date", default=False,
                        help="date to search on. Format YYYY-MM-DD")
    parser.add_argument('-d', '--debug', action="store_true", default=False)
    parser.add_argument("-c", "--config", dest="config_file", default=default_config_file,
                        help="specify config file. Default: "+default_config_file)
    parser.add_argument('-b', '--channel', dest="channel", default=False)
    parser.add_argument('-q', '--quiet', action="store_true", default=False)
    parser.add_argument('-r', '--series', dest="series", default=False)
    parser.add_argument('-l', '--list', action="store_true", default=False)

    global options
    options = parser.parse_args()

    if options.debug:
        global debug
        debug = 1

    global config
    config = get_config(options.config_file)
    if not "username" in config or not "password" in config:
        config_help()
        sys.exit()

    global http
    http = create_http_connection()

    if not options.media:
        options.media = set_media_type(options.type, config)
        
    if options.show:
        search_url = get_show_title_search_url(options.show)
    elif options.full_text:
        search_url = get_full_text_search_url(options.full_text)
    else:
        parser.print_help()
        sys.exit()
        print(search_url)

    programmes = get_programmes(search_url, options.date, options.channel, options.series)

    debug_print(programmes)

    if options.list:
        for programme in programmes:
            list_programme_description(programme)
    else:
        for programme in programmes:
            get_programme_content(programme)
	
if __name__ == "__main__":
    main()

