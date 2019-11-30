#!/bin/python

import argparse
import math
import os
import re
import subprocess
import sys
import tempfile

FNULL = open(os.devnull, 'w')
FFPROBE_BIN = 'ffprobe'
FFPROBE_OPTIONS = [
    '-v', 'error', '-of', 'default=noprint_wrappers=1:nokey=1',
    '-select_streams', 'v:0', '-show_entries', 'stream=duration'
]

FFMPEG_BIN = 'ffmpeg'
FADE_OUT_TIME_SECS = 1

FILTER_TEMPLATE = """
  [0:v]
    format=
      pix_fmts=yuva420p,
    trim=
      start=0:
      end=2,
    gblur=
      sigma=50:
      enable='between(t,0,2)',
    fade=
      t=out:
      st=1:
      d=1:
      alpha=1,
    setpts=PTS-STARTPTS
  [blur_segment];
  [0:v][blur_segment]
    overlay,
    fade=
      t=in:
      st=0:
      d=1:
      alpha=1
  [blur_fade];
  [blur_fade]
    fade=
      t=in:
      st=0:
      d=1,
    fade=
      t=out:
      st={FADE_OUT_START}:
      d=1
  [fade_in_and_out];
  [fade_in_and_out]split[text_base][text_fore];
  [text_fore]
    drawtext=
      text='{TITLE}':
      fontfile={FONT_TITLE}:
      fontsize=150:
      fontcolor=white:
      x=(main_w/2-text_w/2):
      y=(main_h/2-text_h/2)-80,
    drawtext=
      text='{SUBTITLE}':
      fontfile={FONT_SUBTITLE}:
      fontsize=100:
      fontcolor=white:
      x=(main_w/2-text_w/2):
      y=(main_h/2-text_h/2)+80,
    fade=
      t=out:
      st=1:
      d=1:
      alpha=1
  [text_layer];
  [text_base][text_layer]overlay[final];
  [0:a]
    afade=
      t=in:
      st=0:
      d=1,
    afade=
      t=out:
      st={FADE_OUT_START}:
      d=1
  [final_audio]
""".replace(' ', '').replace('\n', '')


def str2bool(v):
  if isinstance(v, bool):
    return v
  if v.lower() in ('yes', 'true', 't', 'y', '1'):
   return True
  elif v.lower() in ('no', 'false', 'f', 'n', '0'):
   return False
  else:
   raise
  argparse.ArgumentTypeError('Boolean value expected.')


arg_parser = argparse.ArgumentParser(
    description='Lo]v[ushasho Quake Live Highlight builder.')
arg_parser.add_argument(
    '--file_name', type=str, required=True, help='The CSV file to process.')
arg_parser.add_argument("--concatenate", type=str2bool, nargs='?',
                        const=True, default=False,
                        help="Generate a single video file.")

args = arg_parser.parse_args()


def log(msg):
  sys.stderr.write('%s\n' % msg)


def get_font_path(font_name):
  fclist_output = subprocess.check_output(
      ['fc-match', '--format=%{file}',
       '%s:style=Regular' % font_name])
  return fclist_output


def get_effective_media_path(file_path):
  # "bash on windows":
  if os.path.isfile('/proc/version'):
    if 'Microsoft' in open('/proc/version').read():
      return file_path.replace('\\', '/')

  # Everything else:
  return file_path


def get_data_from_csv(file_name):
  log('parsing data file: %s' % file_name)

  lines = [l.strip() for l in open(file_name).readlines()]
  data = []
  for line in lines:
    parts = line.split('|')
    data.append({
        'file_name': parts[0],
        'title': parts[1],
        'date': parts[2],
        'start': parts[3],
    })

  log('will process %d videos' % len(data))
  return data


def get_video_duration(file_path):
  effective_file_path = get_effective_media_path(file_path)
  ffprobe_output = subprocess.check_output([FFPROBE_BIN] + FFPROBE_OPTIONS +
                                           [effective_file_path])
  output_lines = ffprobe_output.split('\n')
  return float(output_lines[0].strip())


def trim_video(file_path, start_time):
  log('  trimming ...')
  effective_file_path = get_effective_media_path(file_path)

  _, temp_file_name = tempfile.mkstemp(suffix='_lm.mp4')
  subprocess.check_call(
      [FFMPEG_BIN] + [
          '-y', '-ss', start_time, '-i', effective_file_path, '-c', 'copy',
          temp_file_name
      ],
      stdout=FNULL,
      stderr=FNULL)

  return temp_file_name


def escape(msg):
  return msg.replace('\\', '\\\\').replace('%', '\\\\%').replace(
      '\'', '\'\\\\\\\'\'').replace(":", "\\:")


def apply_filters(file_path, output_file_name, title, subtitle, duration):
  log('  applying filters ...')

  fade_out_start = str(duration - FADE_OUT_TIME_SECS)
  font_trebuchet = get_font_path('Trebuchet MS')
  font_impact = get_font_path('Impact')

  ffmpeg_filter = FILTER_TEMPLATE.replace('{TITLE}', escape(title))
  ffmpeg_filter = ffmpeg_filter.replace('{SUBTITLE}', escape(subtitle))
  ffmpeg_filter = ffmpeg_filter.replace('{FADE_OUT_START}', fade_out_start)
  ffmpeg_filter = ffmpeg_filter.replace('{FONT_TITLE}', font_impact)
  ffmpeg_filter = ffmpeg_filter.replace('{FONT_SUBTITLE}', font_trebuchet)

  subprocess.check_call(
      [FFMPEG_BIN] + [
          '-y', '-i', file_path, '-filter_complex', ffmpeg_filter, '-map',
          '[final]', '-map', '[final_audio]', '-c:v', 'libx264', '-preset',
          'slow', '-profile:v', 'high', '-crf', '18', '-coder', '1', '-pix_fmt',
          'yuv420p', '-movflags', '+faststart', '-g', '30', '-bf', '2', '-c:a',
          'aac', '-b:a', '384k', '-profile:a', 'aac_low', output_file_name
      ],
      stdout=FNULL,
      stderr=FNULL)


def concatenate(file_names, out_file_name):
  log('-----')
  log('writing concatenated file: %s' % out_file_name)

  _, concat_list_file_name = tempfile.mkstemp(suffix='concat_lm.txt')
  concat_list_file = open(concat_list_file_name, 'w')
  concat_list_file.writelines(
      ['file %s\n' % os.path.join(os.getcwd(), n) for n in file_names])
  concat_list_file.close()

  subprocess.check_call(
      [FFMPEG_BIN] + [
          '-f', 'concat', '-safe', '0', '-i', concat_list_file_name, '-c',
          'copy', out_file_name
      ],
      stdout=FNULL,
      stderr=FNULL)


log('input file is %s' % args.file_name)


data = get_data_from_csv(args.file_name)
output_file_names = []
for index, datum in enumerate(get_data_from_csv(args.file_name)):
  title = datum['title']
  date = datum['date']
  file_name = datum['file_name']
  clip_start = datum['start']
  output_file_name = ''.join(
      [c for c in title if c.isalpha() or c.isdigit() or c == ' '] +
      ['.mp4']).rstrip().replace(' ', '_')
  output_file_names.append(output_file_name)

  log('')
  log('-----')
  log('processing video %d/%d:' % (index + 1, len(data)))
  log('- title: %s' % title)
  log('- date: %s' % date)
  log('- clip file: %s' % file_name)
  log('- start time: %s' % clip_start)
  log('- output file: %s' % output_file_name)
  log('')

  trimmed_video_file_name = trim_video(file_name, clip_start)

  apply_filters(trimmed_video_file_name, output_file_name, title, date,
                get_video_duration(trimmed_video_file_name))
  os.remove(trimmed_video_file_name)
  log('done')

if args.concatenate:
  concatenate(output_file_names, args.file_name.replace('csv', 'mp4'))

log('')
log('all done.')
