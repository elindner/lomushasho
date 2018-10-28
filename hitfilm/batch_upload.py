#!/bin/python

"""
Feed a CSV file (separated by pipes) with each line containint:

  media file|title|subtitle|start_time

...a YT playlist, and a directory to look for videos.
"""

import argparse
import os
import re
import subprocess
import sys

UPLOADER_BIN = 'youtube-upload'


def log(msg):
  sys.stderr.write('%s\n' % msg)


def get_data_from_csv(file_name):
  log('parsing data file: %s' % file_name)

  lines = [l.strip() for l in open(file_name).readlines()]
  data = []
  for line in lines:
    parts = line.split('|')
    time_parts = parts[3].split(':')
    seconds = (int(time_parts[0]) * 60) + int(time_parts[1])
    data.append({
        'file_name': parts[0],
        'title': parts[1],
        'date': parts[2].strip(),
        'start': seconds
    })

  log('will upload %d videos' % len(data))
  return data


def escape_path(path):
  escaped = path
  """
  escaped = re.sub(' ', '\\ ', path)
  escaped = re.sub('\'', '\\\'', escaped)
  escaped = re.sub('"', '\\"', escaped)
  escaped = re.sub('\'', '\\\'', escaped)
  escaped = re.sub('!', '\\!', escaped)
  """
  return escaped


def get_file_name(videos_path, title):
  file_name = '%s.mp4' % re.sub('[:\\\\/*?|<>]', '-', title)
  return os.path.join(escape_path(videos_path), escape_path(file_name))


parser = argparse.ArgumentParser(
    description='Batch upload videos to YouTube from a CSV file.')
parser.add_argument('--file_name', type=str, required=True,
                    help='The CSV file to process.')
parser.add_argument('--video_directory', type=str, required=True,
                    help='The directory that contains the videos.')
parser.add_argument('--playlist', type=str, default='QuakeLive',
                    help='The YouTube playlist to add the videos to.')
parser.add_argument('--secrets', type=str, default='',
                    help='OAuth2 secrets file.')

args = parser.parse_args()

input_file_name = args.file_name
log('Input file is %s' % input_file_name)

data = get_data_from_csv(input_file_name)

videos_path = args.video_directory


for datum in data:
  title = datum['title']
  file_name = get_file_name(videos_path, title)
  if not os.path.exists(file_name):
    log('Invalid file: %s' % file_name)
    sys.exit(1)


for index, datum in enumerate(data):
  log('Uploading %2d of %2d' % (index + 1, len(data)))

  description = datum['date'].replace('-', '/')
  title = datum['title']
  file_name = get_file_name(videos_path, title)
  subprocess.call(
      [UPLOADER_BIN] +
      [
          '--privacy=unlisted',
          '--playlist=%s' % args.playlist,
          '--client-secrets=%s' % args.secrets,
          '--description=%s [%d/%d]' % (description, index + 1, len(data)),
          '--title=%s' % title
      ] +
      [file_name])

  log('')

log('')
log('All done.')
