#!/bin/python

"""
Feed a CSV file (separated by pipes) with each line containint:

  media file|title|subtitle|start_time

...like this:

abajo.mp4|Wasabi for the people|4-12-1977|00:30
comela.mp4|comela, mandiok!|8-12-1977|00:00
salgo.mp4|Salgo Coco...|8-12-1977|01:40

NOTE: this requires ffprobe somewhere in PATH
TODO: need to add end_time too
"""

import math
import os
import random
import re
import subprocess
import sys

FFPROBE_BIN = 'ffprobe'
FFPROBE_OPTIONS = [
    '-v', 'error',
    #    '-show_entries', 'stream=avg_frame_rate,duration',
    #    '-show_entries', 'stream=duration',
    '-of', 'default=noprint_wrappers=1:nokey=1',
    '-select_streams', 'v:0']
TITLE_FORMAT_ID = '4437a34d-8d4d-409d-96bf-0f575db70e24'
DATE_FORMAT_ID = '28a10794-27f4-4af7-8201-1d9b048a8af9'
FRAMERATE = 60
CLIP_FRAMERATE = 30
CLIP_LENGTH = 73

COMPOSITION_ASSET_ID = 'f08de726-c1fc-4a37-b6ee-59b33aae2489'
template_path = os.getcwd()


def log(msg):
  sys.stderr.write('%s\n' % msg)


def r(xml, tag, string):
  return xml.replace(tag, string)


def read_template(template_name):
  return ''.join(open(os.path.join(template_path, template_name)).read())


def get_effective_media_path(file_path):
  # "bash on windows":
  if os.path.isfile('/proc/version'):
    if 'Microsoft' in open('/proc/version').read():
      # drive = re.findall(r'/mnt/([a-z])/', file_path)[0].upper()
      # return re.sub(r'/mnt/./', '%s:' % drive, file_path).replace('/', '\\')
      return file_path.replace('\\', '/')

  # Everything else:
  return file_path


def get_hex(size):
  HEX = '0123456789abcdef'
  cs = []
  for i in range(0, size):
    cs.append(random.choice(HEX))
  return ''.join(cs)


def get_id():
  return '-'.join([get_hex(8), get_hex(4), get_hex(4), get_hex(4), get_hex(12)])


def get_media_info(file_path):
  # In bash on windows, the CSV file lists file paths in windows
  # format (D:\path\to\file.mp4) but here we need Unix directories.
  effective_file_path = get_effective_media_path(file_path)

  log('...getting media info for %s' % effective_file_path)
  option = ['-show_entries', 'stream=avg_frame_rate,duration']
  ffprobe_output = subprocess.check_output(
      [FFPROBE_BIN] + FFPROBE_OPTIONS + option + [effective_file_path])
  output_lines = ffprobe_output.split('\n')
  num = int(output_lines[0].strip().split('/')[0])
  den = int(output_lines[0].strip().split('/')[1])
  duration = int(math.floor(float(output_lines[1].strip())))
  return {'frame_rate': float(num) / float(den), 'duration': duration}


def make_paragraph(text, format_id):
  lines = ['<Tk Tp="1" ID="%s" Jf="1"/>' % get_id()]
  for char in text:
    lines.append('<Tk Ch="%d" Tp="0" ID="%s" Ft="%s"/>' % (
        ord(char), get_id(), format_id))
  return ''.join(lines)


def make_text_layer(composition_asset_id, title, date):
  title_format_id = get_id()
  separator_format_id = get_id()
  date_format_id = get_id()

  xml = read_template('text_layer.tmpl')
  xml = r(xml, '{%LAYER_ID%}', get_id())
  xml = r(xml, '{%COMPOSITION_ASSET_ID%}', composition_asset_id)
  xml = r(xml, '{%TITLE_FORMAT_ID%}', title_format_id)
  xml = r(xml, '{%SEPARATOR_FORMAT_ID%}', separator_format_id)
  xml = r(xml, '{%DATE_FORMAT_ID%}', date_format_id)
  xml = r(xml, '{%TITLE%}', make_paragraph(title, title_format_id))
  xml = r(xml, '{%SEPARATOR%}', make_paragraph('  ', separator_format_id))
  xml = r(xml, '{%DATE%}', make_paragraph(date, date_format_id))
  return xml


def make_composition_asset(
        asset_id, title, date, frame_count, solid_layer, media_layer):
  xml = read_template('composition_asset.tmpl')
  xml = r(xml, '{%ASSET_ID%}', asset_id)
  xml = r(xml, '{%TITLE%}', title)
  xml = r(xml, '{%FRAME_COUNT%}', '%d' % frame_count)
  xml = r(xml, '{%TEXT_LAYER%}', make_text_layer(asset_id, title, date))
  xml = r(xml, '{%SOLID_LAYER%}', solid_layer)
  xml = r(xml, '{%MEDIA_LAYER%}', media_layer)
  return xml


def make_media_layer(
        asset_id, layer_id, composition_asset_id, clip_start, end_frame,
        fade_out_start):
  xml = read_template('media_layer.tmpl')
  xml = r(xml, '{%LAYER_ID%}', layer_id)
  xml = r(xml, '{%ASSET_ID%}', asset_id)
  xml = r(xml, '{%BLUR_ID%}', get_id())
  xml = r(xml, '{%COMPOSITION_ASSET_ID%}', composition_asset_id)
  xml = r(xml, '{%CLIP_START%}', '%d' % (clip_start * FRAMERATE))
  xml = r(xml, '{%END_FRAME%}', '%d' % end_frame)
  xml = r(xml, '{%FADE_OUT_START%}', '%d' % fade_out_start)
  xml = r(xml, '{%FADE_OUT_END%}', '%d' % (fade_out_start + 1000))
  return xml


def make_media_asset(
        asset_id, layer_id, composition_asset_id, file_path, frame_rate):
  xml = read_template('media_asset.tmpl')
  xml = r(xml, '{%ASSET_ID%}', asset_id)
  xml = r(xml, '{%LAYER_ID%}', layer_id)
  xml = r(xml, '{%FILE_PATH%}', file_path)
  xml = r(xml, '{%COMPOSITION_ASSET_ID%}', composition_asset_id)
  xml = r(xml, '{%FRAME_RATE%}', '%f' % frame_rate)
  return xml


def make_solid_layer(
        asset_id, layer_id, composition_asset_id, end_frame, fade_out_start):
  xml = read_template('solid_layer.tmpl')
  xml = r(xml, '{%ASSET_ID%}', asset_id)
  xml = r(xml, '{%LAYER_ID%}', layer_id)
  xml = r(xml, '{%COMPOSITION_ASSET_ID%}', composition_asset_id)
  xml = r(xml, '{%END_FRAME%}', '%d' % end_frame)
  xml = r(xml, '{%FADE_OUT_START%}', '%d' % fade_out_start)
  xml = r(xml, '{%FADE_OUT_END%}', '%d' % (fade_out_start + 1000))
  return xml


def make_solid_asset(asset_id, layer_id, composition_asset_id):
  xml = read_template('solid_asset.tmpl')
  xml = r(xml, '{%ASSET_ID%}', asset_id)
  xml = r(xml, '{%LAYER_ID%}', layer_id)
  xml = r(xml, '{%COMPOSITION_ASSET_ID%}', composition_asset_id)
  return xml


def make_asset_list(composition_assets, solid_assets, media_assets):
  def make_id_tags(assets):
    return ''.join(['<ID>%s</ID>' % id for id in assets.keys()])

  xml = read_template('asset_list.tmpl')
  xml = r(xml, '{%COMPOSITION_ASSETS%}', ''.join(composition_assets.values()))
  xml = r(xml, '{%SOLID_ASSETS%}', ''.join(solid_assets.values()))
  xml = r(xml, '{%MEDIA_ASSETS%}', ''.join(media_assets.values()))
  xml = r(xml, '{%COMPOSITION_ASSET_IDS%}', make_id_tags(composition_assets))
  xml = r(xml, '{%SOLID_ASSET_IDS%}', make_id_tags(solid_assets))
  xml = r(xml, '{%MEDIA_ASSET_IDS%}', make_id_tags(media_assets))
  return xml


def make_project(data):
  media_assets = {}
  solid_assets = {}
  composition_assets = {}
  composite_shots = []

  for index, datum in enumerate(data):
    title = datum['title']
    date = datum['date']
    file_name = datum['file_name']
    clip_start = datum['start']

    log('')
    log('-----')
    log('Making composition %d/%d:' % (index + 1, len(data)))
    log('- title: %s' % title)
    log('- date: %s' % date)
    log('- clip file: %s' % file_name)
    log('- start time: %s' % clip_start)

    file_path = file_name
    media_info = get_media_info(file_path)
    media_length = media_info['duration']
    media_frame_rate = media_info['frame_rate']
    frame_count = (media_length - clip_start) * FRAMERATE
    fade_out_start = (media_length - clip_start - 1) * 1000

    composition_asset_id = get_id()
    media_asset_id = get_id()
    media_layer_id = get_id()
    solid_asset_id = get_id()
    solid_layer_id = get_id()

    solid_asset = make_solid_asset(
        solid_asset_id, solid_layer_id, composition_asset_id)
    solid_layer = make_solid_layer(
        solid_asset_id, solid_layer_id, composition_asset_id, frame_count,
        fade_out_start)
    solid_assets[solid_asset_id] = solid_asset

    media_asset = make_media_asset(
        media_asset_id, media_layer_id, composition_asset_id, file_path,
        media_frame_rate)
    media_layer = make_media_layer(
        media_asset_id, media_layer_id, composition_asset_id, clip_start,
        frame_count, fade_out_start)
    media_assets[media_asset_id] = media_asset

    composition_asset = make_composition_asset(
        composition_asset_id, title, date, frame_count, solid_layer,
        media_layer)
    composition_assets[composition_asset_id] = composition_asset

    composite_shots.append(
        '<CompositeShot CompositionId="%s" Name="%s"/>' % (
            composition_asset_id, title))

  asset_list = make_asset_list(
      solid_assets, media_assets, composition_assets)

  xml = read_template('project.tmpl')
  xml = r(xml, '{%ASSET_LIST%}', asset_list)
  xml = r(xml, '{%COMPOSITE_SHOTS%}', ''.join(composite_shots))

  return xml


def get_data_from_csv(template_path, file_name):
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
        'date': parts[2],
        'start': seconds
    })

  log('will create %d compositions' % len(data))
  return data


"""
# Sample data:
DATA = [
    {
        'file_name': 'abajo.mp4',
        'title': 'wasabi for the people',
        'date': '4-12-1977',
        'start': 30
    },
    {
        'file_name': 'salgo.mp4',
        'title': 'Salgo Coco...',
        'date': '8-12-1977',
        'start': 0
    },
]
"""


if len(sys.argv) < 2:
  log('Need a file to process')
  sys.exit(1)

# Find the base directory of the running script, which
# will be used as the base path where to find templates.
template_path = os.path.dirname(sys.argv[0])

file_name = sys.argv[1]
log('Input file is %s' % file_name)

output_file_name = '%s.hfp' % file_name
log('Output file is %s' % output_file_name)

open(output_file_name, 'w').write(
    make_project(get_data_from_csv(template_path, file_name)))

log('')
log('All done.')
