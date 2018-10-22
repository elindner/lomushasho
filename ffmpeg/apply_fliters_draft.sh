#!/bin/bash

if [[ ${#} -lt 3 ]];
then
  echo "${0} <input_file> <output_file> <start_time>"
  exit 1
fi

TITLE="This is a test"
SUBTITLE="20-9-2018"

FFMPEG="$(which ffmpeg)"
FFPROBE="$(which ffprobe)"
INPUT=${1}
OUTPUT=${2}
START_TIME=${3}

get_platform() {
  if [[ "$(uname)" == "Darwin" ]];
  then
    echo "mac"
  else
    if grep -sq Windows /proc/version;
    then
      echo "windows"
    else
      echo "linux"
    fi
  fi
}

get_video_duration() {
  echo $(
    ${FFPROBE} \
      -v error \
      -of default=noprint_wrappers=1:nokey=1 \
      -select_streams v:0 \
      -show_entries stream=duration ${1})
}

get_font_path() {
  echo $(fc-list | grep -Ei "${1}.*\.ttf" | sort | tail -1 | cut -d: -f1)
}

FONT_FILE_TITLE=$(get_font_path Impact)
FONT_FILE_SUBTITLE=$(get_font_path Trebuchet)

echo "Trimming original video..."
TRIMMED_FILE=$(mktemp /tmp/XXXXXXXXX.mp4)

${FFMPEG} \
  -y \
  -i ${INPUT} \
  -ss ${START_TIME} \
  ${TRIMMED_FILE}

VIDEO_DURATION=$(get_video_duration ${TRIMMED_FILE})
FADE_OUT_START=$(bc <<< ${VIDEO_DURATION}-1)

echo "Applying filters..."
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
  [fade_in_and_out];\
  [fade_in_and_out]split[text_base][text_fore];\
  [text_fore]\
    drawtext=\
      text='${TITLE}':\
      fontfile=${FONT_FILE_TITLE}:\
      fontsize=150:\
      fontcolor=white:\
      x=(main_w/2-text_w/2):\
      y=(main_h/2-text_h/2)-80,
    drawtext=\
      text='${SUBTITLE}':\
      fontfile=${FONT_FILE_SUBTITLE}:\
      fontsize=100:\
      fontcolor=white:\
      x=(main_w/2-text_w/2):\
      y=(main_h/2-text_h/2)+80,
    fade=\
      t=out:\
      st=1:\
      d=1:\
      alpha=1\
  [text_layer];\
  [text_base][text_layer]overlay[final];\
  [0:a] \
    afade=\
      t=in:\
      st=0:\
      d=1, \
    afade=\
      t=out:\
      st=${FADE_OUT_START}:\
      d=1 \
  [final_audio]"

${FFMPEG} \
  -y \
  -i ${TRIMMED_FILE} \
  -filter_complex "${FILTER}" \
  -map "[final]" -map "[final_audio]" ${OUTPUT}

rm -f ${TRIMMED_FILE}
