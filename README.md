# libiot
Communicate with smart devices

## Install
These are generic installation instructions.

### To use, permanently
The quickest way to get started is to install the current release from PyPI:
```
pip3 install --user libiot
```

### To use, temporarily
If you prefer to keep .local clean, install to a virtualenv:
```
python3 -m venv venvname
venvname/bin/pip install libiot
. venvname/bin/activate
```

## Commands

### govee
Get data from Govee H5075.

### mijia
Get data from all configured Mijia thermometer/hygrometer 2 sensors.

### p110
Run given command on all configured Tapo P100/P110 plugs.

### temper
Get data from TEMPer USB temperature sensor.
