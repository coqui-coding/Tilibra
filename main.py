from mutagen.id3 import TIT2, TPE1, TDRC, TCON, APIC, TALB, TRCK
from configparser import ConfigParser
from os.path import join as os_join
from bs4 import BeautifulSoup
from mutagen.mp3 import MP3
from pathlib import Path
from io import BytesIO
from PIL import Image
import requests
import datetime
import os


def format_bytes(size):
    power = 2**10
    n = 0
    power_labels = {0: ' bytes', 1: ' KB', 2: ' MB', 3: ' GB', 4: ' TB'}
    while size > power:
        size /= power
        n += 1
    return str(size)[:4] + power_labels[n]


def scan_directory():

    if type_scan == 'a':
        scan_result = [
            root
            for root, dirs, files in os.walk(os_join(os.environ['HOMEPATH'], 'Music'))
            for song in files
            if Path(song).suffix == '.mp3'
        ]
    else:
        scan_result = [
            os_join(folder[0], song)
            for folder in os.walk(music_directory)
            for song in folder[2]
            if Path(song).suffix == '.mp3'
        ]

    if config_file_readings['DEFAULT']['scan_type'] == 'date_created':
        sort_key = os.path.getctime
    elif config_file_readings['DEFAULT']['scan_type'] == 'date_modified':
        sort_key = os.path.getmtime
    else:
        print('ERROR, inappropriate scan type!')
        exit()

    scan_result = sorted(list(set(scan_result)), key=sort_key, reverse=True)

    if config_file_readings['DEFAULT']['scan_limit'] != 'none':
        scan_result = scan_result[:int(config_file_readings['DEFAULT']['scan_limit'])]

    return scan_result


def display_song_details():

    os.system('cls')
    print(path_to_song + '\n')

    if type_scan == 's':
        music_file = MP3(path_to_song)

        comment = None
        image_details = None

        for a in music_file.tags.keys():
            if 'APIC' in a:
                image_details = music_file.tags[a].desc
            elif 'COMM' in a:
                comment = music_file.tags[a]

        print('Title : ' + str(music_file.tags.get('TIT2')))
        print('Artist : ' + str(music_file.tags.get('TPE1')))
        print('Album : ' + str(music_file.tags.get('TALB')))
        print('Date : ' + str(music_file.tags.get('TDRC')))
        print('Track # : ' + str(music_file.tags.get('TRCK')))
        print('Genre : ' + str(music_file.tags.get('TCON')))
        print('Comment : ' + str(comment))
        print('Album Artist : ' + str(music_file.tags.get('TPE2')))
        print('Composer : ' + str(music_file.tags.get('TCOM')))
        print('Disc # : ' + str(music_file.tags.get('TPOS')))
        print('Length : ' + str(datetime.timedelta(seconds=music_file.info.length))[:7])
        print('Size : ' + str(format_bytes(pathlib_song.stat().st_size)))
        print('Cover Art : ' + str(image_details))
    else:
        for song in songs_in_directory:
            print(song)


def search_tags(search):

    # Search for song in discogs

    source = requests.get(f"https://www.discogs.com/search/?q={search}&type=release").text

    soup = BeautifulSoup(source, 'lxml')

    search_results = soup.find(id='search_results')

    link = search_results.div.a['href']

    # Go to first response of the search and parse for tags

    song_source = requests.get('https://www.discogs.com' + link).text

    song_soup = BeautifulSoup(song_source, 'lxml')

    discogs_profile = song_soup.find('div', 'profile')

    profile_title = discogs_profile.find('h1', id='profile_title')

    tracklist = song_soup.find('div', id='tracklist')

    all_div_in_profile_title = discogs_profile.find_all('div')

    tracklist_songs = tracklist.find_all('tr')

    # Retrieve tags

    song_genre, song_date, song_title = '', '', list()
    song_artist, song_album, song_number = '', '', list()

    if type_scan == 's':
        if len(tracklist_songs) > 2:
            for track in tracklist_songs:

                track_title = track.find('span', 'tracklist_track_title').text
                track_artist = track.find('a').text

                if track_title.lower() in search.lower():
                    song_title = list(track_title)
                if ''.join([i for i in track_artist.lower() if not i.isdigit()]).replace(' ()', '') in search.lower():
                    song_artist = ''.join([i for i in track_artist.lower() if not i.isdigit()]).replace(' ()', '').title()
        else:
            song_artist = profile_title.span.span.a.text.strip()

            song_title = profile_title.find_all('span')[2].text.strip()

        for data in all_div_in_profile_title:

            data_text = data.text
            data_index = all_div_in_profile_title.index(data)

            if data_text.strip().lower() == 'genre:':
                song_genre = all_div_in_profile_title[data_index + 1].text.strip()
                if ',' in song_genre:
                    song_genre = song_genre.split(', ')[0]
            elif data_text.strip().lower() == 'year:':
                song_date = all_div_in_profile_title[data_index + 1].text.strip()
            elif data_text.strip().lower() == 'released:':
                song_date = all_div_in_profile_title[data_index + 1].text.strip().split(' ')[-1]
    else:
        song_artist = profile_title.span.span.a.text.strip()
        song_album = profile_title.find_all('span')[2].text.strip()

        for track in tracklist_songs:

            track_title = track.find('span', 'tracklist_track_title').text
            song_number.append(track.find('td', 'tracklist_track_pos').text)

            for song in songs_in_directory:
                if track_title.lower() in song.lower():
                    song_title.append(track_title)

        for data in all_div_in_profile_title:

            data_text = data.text
            data_index = all_div_in_profile_title.index(data)

            if data_text.strip().lower() == 'genre:':
                song_genre = all_div_in_profile_title[data_index + 1].text.strip()
                if ',' in song_genre:
                    song_genre = song_genre.split(', ')[0]
            elif data_text.strip().lower() == 'year:':
                song_date = all_div_in_profile_title[data_index + 1].text.strip()
            elif data_text.strip().lower() == 'released:':
                song_date = all_div_in_profile_title[data_index + 1].text.strip().split(' ')[-1]

    # Get cover art

    image_source = song_soup.find('span', 'thumbnail_center').img['src']

    response = requests.get(image_source)

    image = Image.open(BytesIO(response.content))

    return {
        'title': song_title,
        'artist': song_artist,
        'album': song_album,
        'genre': song_genre,
        'year': song_date,
        'track_number': song_number,
        'image_src': image_source,
        'image': image
    }


def write_tags():
    if type_scan == 's':
        music = MP3(path_to_song)

        b = BytesIO()
        results['image'].save(b, format='PNG')

        music.tags.add(TIT2(text=results['title']))
        music.tags.add(TPE1(text=results['artist']))
        music.tags.add(TDRC(text=results['year']))
        music.tags.add(TCON(text=results['genre']))
        music.tags.add(APIC(data=b.getvalue(), mime='image/png'))

        music.tags.save(path_to_song, pathlib_song.name)
    else:
        for s in songs_in_directory:
            if Path(s).suffix != '.mp3':
                continue

            song_path = os_join(path_to_song, s)
            music = MP3(song_path)

            for s_number, s2 in zip(results['track_number'], results['title']):
                if s2.lower() in s.lower():
                    music.tags.add(TIT2(text=s2))
                    music.tags.add(TRCK(text=s_number))
                    break

            b = BytesIO()
            results['image'].save(b, format='PNG')

            music.tags.add(TPE1(text=results['artist']))
            music.tags.add(TDRC(text=results['year']))
            music.tags.add(TCON(text=results['genre']))
            music.tags.add(TALB(text=results['album']))
            music.tags.add(APIC(data=b.getvalue(), mime='image/png'))

            music.tags.save(song_path, pathlib_song.name)


def read_config():

    if not pathlib_config_file.exists():
        pathlib_config_file.touch()

        config = ConfigParser()

        config['DEFAULT'] = {
            'music_directory': os_join(os.environ['HOMEPATH'], 'Music'),
            '; use date_created or date_modified': '',
            'scan_type': 'date_created',
            '; use None or a number to maximize the songs shown': '',
            'scan_limit': 'None'
        }

        with open(config_file_path, 'w') as configFile:
            config.write(configFile)

    config = ConfigParser()

    config.read(config_file_path)

    return config


if __name__ == '__main__':

    config_file_path = 'config.ini'
    pathlib_config_file = Path(config_file_path)

    config_file_readings = read_config()

    music_directory = config_file_readings['DEFAULT']['music_directory']

    type_scan = input('Do you want to scan for albums(a) or songs(s)?')
    all_songs = scan_directory()

    os.system('cls')

    for song_directory in all_songs[::-1]:
        print(all_songs.index(song_directory), Path(song_directory).name)

    if type_scan == 's':
        print(f'\nDetected {len(all_songs)} songs')
    else:
        print(f'\nDetected {len(all_songs)} albums')

    choice = input('\nWhat song do you want to tagify?\n')

    path_to_song = all_songs[int(choice)]
    pathlib_song = Path(path_to_song)

    songs_in_directory = os.listdir(path_to_song) if type_scan == 'a' else ''

    display_song_details()

    search_choice = input('\nDo you want to search for possible tags?[y]\n')
    if search_choice != 'y':
        exit()

    query = input('\nQuery [press enter for filename or provide artist and song name]: ')
    if query == '':
        query = pathlib_song.stem

    try:
        results = search_tags(query)
    except ConnectionError as error:
        os.system('cls')
        print('You must be connected to the internet!')
        os.system('pause')
        exit()

    results['image'].show()
    image_name = os.path.splitext(results['image_src'].split('/')[-1])[0]

    if type_scan == 's':
        print('Title : ' + str(results['title']))
        print('Artist : ' + results['artist'])
        print('Genre : ' + results['genre'])
        print('Year : ' + results['year'])
    else:
        print('Songs found :')
        for song_number, song in zip(results['track_number'], results['title']):
            print(f'\t{song_number} {song}')
        print('Album : ' + results['album'])
        print('Artist : ' + results['artist'])
        print('Genre : ' + results['genre'])
        print('Year : ' + results['year'])

    print('Image Source: ' + results['image_src'])

    write_choice = input('\nAre you sure you want to tagify?[y]\n')
    if write_choice != 'y':
        exit()

    write_tags()
