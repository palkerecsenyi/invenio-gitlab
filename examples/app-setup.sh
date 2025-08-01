#!/bin/sh

# quit on errors:
set -o errexit

# quit on unbound symbols:
set -o nounset

DIR=`dirname "$0"`

cd $DIR
export FLASK_APP=app.py

# Setup app
mkdir $DIR/instance

# install dependencies
npm install -g --unsafe-perm node-sass clean-css@3 requirejs uglify-js webpack

# install assets
flask npm
cd static
npm install
cd ..
flask collect -v
! flask webpack buildall
flask assets build


# Create the database
flask db init
flask db create
