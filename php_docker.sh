#!/usr/bin/env sh

dockerphp() {
  filepath=$(dirname $(realpath $1))
  filename=$(basename $(realpath $1))

  docker run --rm -v $filepath:/myfiles --entrypoint "php" php:5.6.2 /myfiles/$filename
}

dockerphp $1