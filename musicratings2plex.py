# musicratings2plex.py
# Sync rating tags from FLAC and mp3 files to a Plex server

import re,pathlib,mutagen,plexapi,logging,sys

from mutagen.flac import FLAC
from mutagen.id3 import ID3
from plexapi.server import PlexServer
from configparser import ConfigParser

logging.basicConfig(level=logging.INFO,filename='error.log',
filemode='w', format='%(name)s - %(levelname)s - %(message)s')

if not len(sys.argv) == 2:
    print('Usage: musicratings2plex.py $m3ufile')
    exit(1)

#Read config.ini file
config_object = ConfigParser()
config_object.read('config.ini')

#Plex Server Settings
plexsettings = config_object['PLEX']
plexbaseurl = plexsettings['plexbaseurl']
plextoken = plexsettings['plextoken']
plex = PlexServer(plexbaseurl, plextoken)
musiclibrary = plex.library.section(plexsettings['musiclibrary'])

m3ufile = open(sys.argv[1], 'r')

def read_flac_tags():
    global trackartist
    global trackalbum
    global tracktitle
    global trackrating
    flacfile = FLAC(audiofile)
    trackartist = flacfile["ARTIST"]
    trackartist = trackartist[0]
    tracktitle = flacfile["TITLE"]
    tracktitle = tracktitle[0]
    if not (flacfile.pprint().find("\nALBUM=")) == -1:
        trackalbum = flacfile["ALBUM"]
        trackalbum = trackalbum[0]
    else:
        trackalbum = ""
    trackrating = flacfile["RATING"]
    trackrating = trackrating[0]
    trackrating = float(trackrating) * .1

def read_id3_tags():
    global trackartist
    global trackalbum
    global tracktitle
    global trackrating
    mp3file = mutagen.File(audiofile)
    trackartist = mp3file.tags.get("TPE1")[0]
    if mp3file.tags.get("TALB"):
        trackalbum = mp3file.tags.get("TALB")[0]
    else:
        trackalbum = ""
    tracktitle = mp3file.tags.get("TIT2")[0]
    trackrating = mp3file.tags.getall("POPM")[0]
    trackrating = re.search('rating=(.+?),', str(trackrating)).group(1)
    trackrating = float(trackrating)
    convert_id3_rating(trackrating)

def convert_id3_rating(x):
    global trackrating
    logging.info("trackrating = %s", trackrating)
    if x == 0:
        trackrating = 0
    elif 1 <= x <= 49:
        trackrating = 1
    elif x == 50:
        trackrating = 2
    elif 51 <= x <= 99:
        trackrating = 3
    elif x == 100:
        trackrating = 4
    elif 101 <= x <= 149:
        trackrating = 5
    elif x == 150:
        trackrating = 6
    elif 151 <= x <= 199:
        trackrating = 7
    elif x == 200:
        trackrating = 8
    elif 201 <= x <= 249:
        trackrating = 9
    elif 250 <= x <= 255:
        trackrating = 10
    logging.info("Converted rating: %s", trackrating)

def print_track_info():
    global trackartist
    global trackalbum
    global tracktitle
    global trackrating
    print("Current audio file: " + audiofile)
    print(" ")
    print("Artist: " + trackartist)
    print("Album: " + trackalbum)
    print("Track: " + tracktitle)
    print("Rating: " + str(trackrating))
    print(" ")

def sync_rating_to_plex():
    global trackartist
    global trackalbum
    global tracktitle
    global trackrating
    trackartist = re.sub(r'[^A-Za-z0-9é /<>\[\]:.$()&\'\"-]', "", trackartist)
    trackalbum = re.sub(r'[^A-Za-z0-9é /<>\[\]:.$()&\'\"-]', "", trackalbum)
    tracktitle = re.sub(r'[^A-Za-z0-9é /<>\[\]:.$()&\'\"-]', "", tracktitle)
    print(trackartist + " - " + trackalbum + " - " + tracktitle)
    if not trackalbum:
        trackalbum = ""
    if musiclibrary.searchTracks(filters={"artist.title": trackartist, "album.title": trackalbum, "track.title": tracktitle}):
        plextrack = musiclibrary.searchTracks(filters={"artist.title": trackartist, "album.title": trackalbum, "track.title": tracktitle})[0]
        plextrack.rate(trackrating)
        print("Rating sync'd to Plex: " + str(trackrating))
        print_line()
    elif musiclibrary.searchTracks(filters={"artist.title": trackartist, "track.title": tracktitle}):
        plextrack = musiclibrary.searchTracks(filters={"artist.title": trackartist, "track.title": tracktitle})[0]
        plextrack.rate(trackrating)
        print("Rating sync'd to Plex: " + str(trackrating))
        print_line()
    elif musiclibrary.searchTracks(filters={"album.title": trackalbum, "track.title": tracktitle}):
        plextrack = musiclibrary.searchTracks(filters={"album.title": trackalbum, "track.title": tracktitle})[0]
        plextrack.rate(trackrating)
        print("Rating sync'd to Plex: " + str(trackrating))
        print_line()
    else:
        logging.info("%s not found on Plex server", tracktitle)
        print("Track could not be found on Plex server")
        print_line()

def print_line():
    print("---------------------------------------------------------------")

# Main stuff
count = 0
index = -1
while True:
    count += 1
    index += 1
    audiofile = m3ufile.readline()
    audiofile = audiofile.rstrip('\n')
    print(audiofile)
    extension = pathlib.Path(audiofile).suffix
    if extension == '.flac':
        print("Reading tags of FLAC file")
        read_flac_tags()
    elif extension == '.mp3':
        read_id3_tags()
    if not audiofile:
        break
    print_line()
    print_track_info()
    sync_rating_to_plex()
    print_line()