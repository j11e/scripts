#!/usr/bin/env sh

# exercise to the reader: add support for composer intall/update
# maybe a simple "if $2 == composer" (with a tad more cleverness in case there a path to follow, etc)
# that mounts some additional folders and composes the corresponding docker command

dockerphp() {
  filepath=$(dirname $(realpath $1))
  filename=$(basename $(realpath $1))

  docker run --rm -v $filepath:/myfiles --entrypoint "php" php:5.6.2 /myfiles/$filename
}

dockerphp $1
