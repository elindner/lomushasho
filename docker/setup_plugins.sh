#!/bin/bash

git clone https://github.com/MinoMino/minqlx-plugins.git core-plugins
mkdir plugins
cp core-plugins/*.py plugins/
cp ../minqlx/*.py plugins/
