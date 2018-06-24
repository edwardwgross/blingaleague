import datetime
import os

from apiclient.discovery import build
from apiclient.http import MediaIoBaseDownload
from httplib2 import Http
from oauth2client import file, client, tools

from django.conf import settings
from django.core.management.base import BaseCommand

from blingacontent.models import Gazette


class Command(BaseCommand):

    def handle(self, *args, **kwargs):
        client_secret_file = '/data/blingaleague/data/client_secret.json'
        # Setup the Drive v3 API
        SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.appdata',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.metadata',
            'https://www.googleapis.com/auth/drive.metadata.readonly',
            'https://www.googleapis.com/auth/drive.photos.readonly',
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.scripts',
        ]
        store = file.Storage('credentials.json')
        creds = store.get()
        if not creds or creds.invalid:
            flow = client.flow_from_clientsecrets(client_secret_file, SCOPES)
            creds = tools.run_flow(flow, store)
        service = build('drive', 'v2', http=creds.authorize(Http()))

        file_list = service.children().list(
            folderId='0BzjwZZ1eHJfnaTlxSjF5eTFiYWc',
            maxResults=1000,
            orderBy='createdDate',
        ).execute().get('items', [])

        for f in file_list:
            metadata = service.files().get(fileId=f['id']).execute()
            if metadata.get('labels', {}).get('trashed', False):
                continue
            title = metadata['title'].strip()
            if title.endswith('.txt'):
                title = title[:-4]
            try:
                parts = title.split(' ')
                date_str = parts[0]
                date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
                headline = ' '.join(parts[1:])
                request = service.files().get_media(fileId=f['id'])
                with open('/data/blingaleague/data/gazettes/temp.txt', 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while done is False:
                        status, done = downloader.next_chunk()
                with open('/data/blingaleague/data/gazettes/temp.txt', 'rb') as fh:
                    body = fh.read().decode('utf-8')
                gazette, _created = Gazette.objects.get_or_create(
                    headline=headline,
                    published_date=date_obj
                )
                gazette.body = body
                gazette.save()
                print("SUCCESS: {}".format(gazette))
            except Exception as e:
                print("ERROR doing {}".format(title))
                print(e)
