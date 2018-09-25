#!/bin/bash

if [[ ${#} -lt 2 ]];
then
  echo "${0} <input_file> <output_file> <start_time>"
  exit 1
fi

TITLE="This is a test"

FFMPEG="/usr/bin/ffmpeg"
FFPROBE="/usr/bin/ffprobe"
INPUT=${1}
OUTPUT=${2}

VIDEO_DURATION=$(
  ${FFPROBE} \
    -v error \
    -of default=noprint_wrappers=1:nokey=1 \
    -select_streams v:0 \
    -show_entries stream=duration ${INPUT})

FADE_OUT_START=$(bc <<< ${VIDEO_DURATION}-1)

FILTER="\
  [0:v] \
    format= \
      pix_fmts=yuva420p,
    trim= \
      start=0: \
      end=2, \
    gblur= \
      sigma=50: \
      enable='between(t,0,2)', \
    fade= \
      t=out: \
      st=1: \
      d=1: \
      alpha=1, \
    setpts=PTS-STARTPTS \
  [blur_segment]; \
  [0:v][blur_segment] \
    overlay, \
    fade=\
      t=in:\
      st=0:\
      d=1: \
      alpha=1 \
  [blur_fade];
  [blur_fade] \
    fade=\
      t=in:\
      st=0:\
      d=1, \
    fade=\
      t=out:\
      st=${FADE_OUT_START}:\
      d=1\
  [blur_fade_from_black];\
  [blur_fade_from_black]split[text_base][text_fore];\
  [text_fore]\
    drawtext=\
      text='${TITLE}':\
      font=Impact:\
      fontsize=150:\
      fontcolor=white:\
      x=(main_w/2-text_w/2):\
      y=(main_h/2-text_h/2),
    fade=\
      t=out:\
      st=1:\
      d=1:\
      alpha=1\
  [text_layer];\
  [text_base][text_layer]overlay[final]"

${FFMPEG} \
  -y \
  -i ${INPUT} \
  -filter_complex "${FILTER}" \
  -map "[final]" ${OUTPUT}
