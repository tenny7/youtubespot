"""
Youtube spotify app
"""

import os
import json
import requests

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import youtube_dl

from secrets import spotify_user_id, spotify_token, youtube_api_key


class CreatePlaylist:
    def __init__(self):
        self.user_id = spotify_user_id
        self.spotify_token = spotify_token
        self.youtube_client = self.get_youtube_client()
        self.all_song_info = {}

    def get_youtube_client(self):
        # Disable OAuthlib's HTTPS verification when running locally.
        # *DO NOT* leave this option enabled in production.
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

        api_service_name = "youtube"
        api_version = "v3"
        client_secrets_file = "client_secret.json"

        print(client_secrets_file)

        # Get credentials and create an API client
        scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(client_secrets_file, scopes)
        credentials = flow.run_console()

        # from youtube Data API
        youtube_client = googleapiclient.discovery.build(api_service_name, api_version, credentials=credentials)

        return youtube_client

    # Grab our liked videos and creating a dictionary of important song information
    def get_liked_videos(self):
        request = self.youtube_client.videos().list(
            part="snippet,contentDetails,statistics",
            myRating="like"
        )

        response = request.executes()
        # collect each video and get important information
        for item in response["items"]:
            video_title = item["snippet"]["title"]
            youtube_uri = "https://www.youtube.com/watch?v={}".format(item["id"])

        # use youtube_dl to collect song name and artist
        video = youtube_dl.YoutubeDL({}).extract_info(youtube_uri, download=False)

        song_name = video["track"]
        artist = video["artist"]

        # save al inortan details
        self.all_song_info[video_title] = {
            "youtube_url": youtube_uri,
            "song_name": song_name,
            "artist": artist,
            # add uri, easy to get song to put inside playlist
            "spotify_uri": self.get_spotify_uri(song_name, artist)
        }

    def create_playlist(self):
        request_body = json.dumps({
            "name": "Youtube liked videos",
            "description": "All liked youtube videos",
            "public": True,
        })
        query = "https://api.spotify.com/v1/users/{}/playlists".format(self.user_id)
        response = requests.post(
            query,
            data=request_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json("id")

    def get_spotify_uri(self, song_name, artist):
        # query2 = "https://api.spotify.com/v1/search?query=track=&type=artist&offset=5&limit=10"
        query = "https://api.spotify.com/v1/search?query=track%3A{}+artist%3A{}&type=track&offset=0&limit=10".format(
            song_name,
            artist
        )
        response = requests.post(
            query,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(spotify_token)
            }
        )
        response_json = response.json()
        songs = response_json["tracks"]["items"]

        uri = songs[0]["uri"]
        return uri

    def add_song_to_playlist(self):

        self.get_liked_videos()

        uris = []
        for song, info in self.all_song_info.items():
            uris.append(info["spotify_uri"])

        # create a new playlisy
        playlist_id = self.create_playlist()
        request_data = json.dumps(uris)

        query = "https://api.spotify.com/v1/playlists/{}/tracks".format(playlist_id)

        response = requests.post(
            query,
            data=request_data,
            header={
                "Content-Type": "application/json",
                "Authorization": "Bearer {}".format(self.spotify_token)
            }
        )
        # yes

        response_json = response.json()
        return response_json
