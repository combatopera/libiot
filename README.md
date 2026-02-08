# libiot
Communicate with smart devices.

## Install
These are generic installation instructions.

### To use, disposably
Install the current release from PyPI to a virtual environment:
```
python3 -m venv venvname
venvname/bin/pip install -U pip
venvname/bin/pip install libiot
. venvname/bin/activate
```

### To use, permanently
```
pip3 install --break-system-packages --user libiot
```
See `~/.local/bin` for executables.

### To develop
First install venvpool to get the `motivate` command:
```
pip3 install --break-system-packages --user venvpool
```
Get codebase and install executables:
```
git clone git@github.com:combatopera/libiot.git
motivate libiot
```
Requirements will be satisfied just in time, using sibling projects with matching .egg-info if any.

## Commands

### govee
Get data from Govee H5075.

### mijia
Get data from all configured Mijia thermometer/hygrometer 2 sensors.

### p110
Run given command on all configured Tapo P100/P110 plugs.
