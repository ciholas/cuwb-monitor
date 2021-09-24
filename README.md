# CUWB Monitor

The CUWB Monitor provides an interface for gathering and visualizing data from a CUWB Network.

## Setup
Use `virtualenv` to run the CUWB Monitor. `virtualenv` is a tool to create isolated Python environments. You can install it via apt on Ubuntu or brew on macOS.

### Create a virtual environment
```bash
$ virtualenv venv --python=python3
```

### Activate a virtual environment
```bash
$ source venv/bin/activate
```

### Install dependencies
```bash
(venv)$ pip install -r requirements.txt
(venv)$ sudo apt install libxkbcommon-x11-0 libxcb-xinerama0
```

### Exit the virtual environment
```bash
(venv)$ deactivate
```

## Usage
Run the CUWB Monitor from inside the `virtualenv` "venv".

```bash
(venv)$ ./CuwbMonitor.py -h
```

## License

This work is licensed under the [Creative Commons Attribution 4.0 International](http://creativecommons.org/licenses/by/4.0/) License.
