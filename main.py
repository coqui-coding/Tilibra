from mutagen.id3 import TIT2, TPE1, TDRC, TCON, APIC
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
    power_labels = {0: 'bytes', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return size, power_labels[n]


def scan_directory():

    songs = [
        os_join(folder[0], song)
        for folder in os.walk(music_directory)
        for song in folder[2]
        if Path(song).suffix == '.mp3'
    ]

    return sorted(songs, key=os.path.getctime, reverse=True)


def display_song_details(path_of_song):

    os.system('cls')
    print(path_of_song + '\n')

    music_file = MP3(path_of_song)

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
    print('Size : ' + str(format_bytes(Path(path_of_song).stat().st_size))[1:5] + 'MB')
    print('Cover Art : ' + str(image_details))


def search_tags():

    # Search for song in discogs

    source = requests.get(f"https://www.discogs.com/search/?q={Path(song_path).stem}&type=all").text

    soup = BeautifulSoup(source, 'lxml')

    search = soup.find(id='search_results')

    link = search.div.a['href']

    # Go to first response of the search and parse for tags

    song_source = requests.get('https://www.discogs.com' + link).text

    song_soup = BeautifulSoup(song_source, 'lxml')

    discogs_profile = song_soup.find('div', 'profile')

    song_title_artist = discogs_profile.find('h1', id='profile_title')

    song_date_genre = discogs_profile.find_all('div')

    # Retrieve tags

    song_artist = song_title_artist.span.span.a.text.strip()

    song_title = song_title_artist.find_all('span')[2].text.strip()

    song_date = song_date_genre[5].text.strip()

    song_genre = song_date_genre[3].text.strip()

    # Get cover art

    image_source = song_soup.find('span', 'thumbnail_center').img['src']

    response = requests.get(image_source)

    image = Image.open(BytesIO(response.content))

    return {
        'title': song_title,
        'artist': song_artist,
        'genre': song_genre,
        'year': song_date,
        'image_src': image_source,
        'image': image
    }


def write_tags():
    mus = MP3(song_path)

    b = BytesIO()
    results['image'].save(b, format='PNG')

    mus.tags.add(TIT2(text=results['title']))
    mus.tags.add(TPE1(text=results['artist']))
    mus.tags.add(TDRC(text=results['year']))
    mus.tags.add(TCON(text=results['genre']))
    mus.tags.add(APIC(data=b.getvalue(), mime='image/png'))

    mus.tags.save(song_path, Path(song_path).name)


if __name__ == '__main__':

    music_directory = os.path.join(os.environ['HOMEPATH'], 'Music')
    all_songs = scan_directory()

    for song_directory in all_songs[::-1]:
        print(all_songs.index(song_directory), Path(song_directory).name)

    print(f'\nDetected {len(all_songs)} songs')

    choice = input('\nWhat song do you want to tagify?\n')

    song_path = all_songs[int(choice)]

    display_song_details(song_path)

    search_choice = input('\nDo you want to search for possible tags?[y]\n')
    if search_choice != 'y':
        exit()

    results = search_tags()
    results['image'].show()
    image_name = os.path.splitext(results['image_src'].split('/')[-1])[0]

    print('Title : ' + results['title'])
    print('Artist : ' + results['artist'])
    print('Genre : ' + results['genre'])
    print('Year : ' + results['year'])
    print('Image Source: ' + results['image_src'])

    write_choice = input('\nAre you sure you want to tagify?[y]\n')
    if write_choice != 'y':
        exit()

    write_tags()
