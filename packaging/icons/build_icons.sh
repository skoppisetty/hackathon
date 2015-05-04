#!/bin/bash
# Given base.png and base32.png, makes the various sizes of icons needed for
# OS X and Windows, and puts them into .icns and .ico files, respectively.
# To run this script, make sure you have png2icns (icnsutils) and imagemagick
# installed. On Debian, that means you should run:
#     sudo aptitude install icnsutils imagemagick

ICN_PREFIX=idigbio-marks_idigbio-mark-
ICN_16="${ICN_PREFIX}16.png"
ICN_48="${ICN_PREFIX}48.png"
ICN_128="${ICN_PREFIX}128.png"
ICN_605="${ICN_PREFIX}605.png"

echo "Setting Up"
rm -rf osx_icon win_icon
mkdir -p osx_icon win_icon

echo "Rescaling and Copying OS X Icons"
convert $ICN_605 -resize 512x512 osx_icon/icn512.png
convert $ICN_605 -resize 256x256 osx_icon/icn256.png
cp $ICN_128 osx_icon/icn128.png
cp $ICN_48 osx_icon/icn48.png
convert $ICN_48 -resize 32x32 osx_icon/icn32.png
cp $ICN_16 osx_icon/icn16.png

echo "Building OS X .icns File"
png2icns osx_icon/icon.icns osx_icon/*.png > /dev/null # quiet, you!


echo "Rescaling and Converting Windows Icons"
convert $ICN_605 -resize 256x256 win_icon/icn256.bmp
convert $ICN_48 win_icon/icn48.bmp
convert $ICN_48 -resize 32x32 win_icon/icn32.bmp
convert $ICN_16 win_icon/icn16.bmp

echo "Building Windows .ico File"
convert win_icon/*.bmp win_icon/icon.ico


echo "Cleaning Up"
rm osx_icon/*.png win_icon/*.bmp
