# Polygon Uploader
uploader of tasks to polygon.codeforces.com

## Installation

`pip install polygon-uploader`

## Usage, usaco module

`usacoimport <usaco_cp_id> <usaco_name> <polygon id>`

`usacoimport 1020 deleg_platinum_feb20 123123`

`usaco_cp_id` is taken from the problem description link, for example: http://usaco.org/index.php?page=viewproblem2&cpid=1020, in this example `usaco_cp_id` is `1020`

`usaco_id` is taken from testdata link, for example: http://usaco.org/current/data/deleg_platinum_feb20.zip, in this example `usaco_id` is `deleg_platinum_feb20`

## Usage, domjudge module

`domjudgeimport <problem_directory> <polygon problem id> [--create]`

`domjudgeimport bapc2022/adjustedaverage 123123`

`--create` -- creates new problem in polygon if no problem with the provided ID was found

## Config file

Config file is located in `<user dir>/.config/polygon-uploader`

Uploads to https://polygon.codeforces.com by default, change the config file to upload to a different instace of polygon
