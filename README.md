# CUWB Monitor

The CUWB Monitor provides an interface for gathering and visualizing data from a CUWB Network.

## Setup

This program requires use of Python 3.7+

Please see 'requirements.txt' for required libraries.

Below describes how to setup and use a python virtual environment to run the code. Using a virtual environment is recommended to ensure all necessary packages are installed.

### Install virtualenv tools

Install the python3-dev and gcc packages.

Install the virual environment package to create and use the virtual environment

```bash
$ pip install virtualenv
```

### Create a virtual environment

The following command will create a virtual in the local directory. Replace [NamedEnv] with an appropriate name for the environment

```bash
$ virtualenv [NamedEnv] --python=python3
```

### Activate the created virtualenv

You can activate the python environment by running the following command (be sure to replace [NamedEnv] with the name used when creating the environment):

Mac OS / Linux
```bash
$ source [NamedEnv]/bin/activate
```
Windows
```
$ [NamedEnv]\Scripts\activate
```
You should see the name of your virtual environment in brackets on your terminal line e.g. ([NamedEnv]).

### Install necessary packages

If pip is installed on the target system, the following commands can be used to install the required packages.

```bash
([NamedEnv])$ pip install --upgrade pip
([NamedEnv])$ pip install -r requirements.txt
```

### Exit the virtual environment

```bash
([NamedEnv])$ deactivate
```

## Usage

Run from inside the virtualenv. See [Activating the created virtualenv](#activate-the-created-virtualenv) in setup section above.


Linux
```bash
([NamedEnv])$ ./CuwbMonitor.py -h
```

Windows
```bash
([NamedEnv])$ python CuwbMonitor.py -h
```

## Troubleshooting

### Outdated Pip

If during your `pip install -r requirements.txt` the install hangs or throws an error like the following at the `Preparing wheel metadata...` stage,

```
Error: Command errored out with exit status 1: path/to/cuwb-monitor/([NamedEnv])/bin/python /tmp/tmplurglly0 prepare_metadata_for_build_wheel /tmp/tmp3sg9b80kCheck the logs for full command output.
```

run the following command to ensure your pip version is up to date.

```bash
$ pip install --upgrade pip
```

### Missing python3-dev

If during your `pip install -r requirements.txt` the install throws an error ending with the following at the `Building wheels for installed packages: PyOpenGL_accelerate` stage,

```
src/wrapper.c:6:10: fatal error: Python.h: No such file or directory
    6 | #include "Python.h"
      |          ^~~~~~~~~
compilation terminated.
error:command '/usr/bin/x86_64-linux-gnu-gcc' failed with exit code 1
[end of output]

note: This error originates from a subprocess, and is likely not a problem with pip.
error: legacy-install-failure

Encountered error while trying to install the package.
  PyOpenGL_accelerate

note: This is an issue with the package mentioned above, not pip.
hint: See above for output from the failure.
```

ensure that you have the python3-dev package(s) installed.

Linux with apt package manager
```bash
$ sudo apt-get install python3-dev
```

### Missing GCC

If during your `pip install -r requirements.txt` the install throws an error ending with the following,

```
unable to execute 'x86_64-linux-gnu-gcc': No such file or directory
error: command 'x86_64-linux-gnu-gcc failed with exit status 1
[end of output]

note: This error originates from a subprocess and is likely not a problem with pip.
error: legacy-install-failure

Encountered error while trying to install package PyOpenGL_accelerate
```

Ensure you have the gcc package(s) installed.

Linux with apt package manager
```bash
$ sudo apt-get install gcc
```

## Documentation

### More Information on Virtual Environments

[Virtual Environment Tutorial](https://docs.python.org/3/tutorial/venv.html)

[installing and Using pip and virtual environments](https://packaging.python.org/guides/installing-using-pip-and-virtual-environments/)

[Creating a Virtual Environment](https://docs.python.org/3/library/venv.html)

## License

This work is licensed under the [Creative Commons Attribution 4.0 International](http://creativecommons.org/licenses/by/4.0/) License.
