# SENAITE AD/LDAP Plugin

PAS Plugin for AD/LDAP


## How to install SENAITE AD/LDAP Plugin?

The following steps will guide you through the installation procedure on a [Debian](https://www.debian.org/) server system.

However, [SENAITE](https://www.senaite.com) also runs on other distributions such as. [Ubuntu](https://ubuntu.com), [SUSE](https://www.suse.com/), etc. and other Unix and Unix-like systems such as [FreeBSD](https://www.freebsd.org/) and  [MacOS](https://de.wikipedia.org/wiki/MacOS).

**tip**

    Use a virtualization environment such as [VirtualBox](https://www.virtualbox.org) or [VMWare](https://www.vmware.com/products/desktop-hypervisor/workstation-and-fusion) to locally install a dedicated Debian VM.


### Install a Python 2.x interpreter

SENAITE 2.x still requires [Python 2.7](https://docs.python.org/2/index.html)!
If you no longer have Python 2.7 on your computer, you should therefore install it with [pyenv](https://github.com/pyenv/pyenv#readme).

Also read [this upgrade guide](https://github.com/senaite/senaite.core/blob/2.x/P8_UPGRADE_GUIDE.md) for our further plans to make SENAITE 3.x fully compatible with Python 3.


#### Install pyenv

[Pyenv](https://github.com/pyenv/pyenv) is a simple Python version management environment that lets you easily install and switch between multiple versions of Python.
It's simple, unobtrusive, and follows the UNIX tradition of single-purpose tools that do one thing well.

**info "Package Requirements"**

    This step requires manual installation of the following packages:
    
    ```
    sudo apt install git build-essential libbz2-dev zlib1g-dev libssl-dev libsqlite3-dev libffi-dev uuid-dev libnss3-dev libgdbm-dev libgdbm-compat-dev libncursesw5-dev liblzma-dev libreadline-dev
    ```

Install pyenv via the [official installer script](https://github.com/pyenv/pyenv?tab=readme-ov-file#a-getting-pyenv):

``` shell
curl https://pyenv.run | bash
```

Please follow these instructions on [how to setup your shell environment](https://github.com/pyenv/pyenv?tab=readme-ov-file#b-set-up-your-shell-environment-for-pyenv) after successful installation.


**info "TL;DR"**

    If you are a [ZSH](https://www.zsh.org/) user add this to your `~/.zshrc`:

    ```shell
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.zshrc
    echo '[[ -d $PYENV_ROOT/bin ]] && export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.zshrc
    echo 'eval "$(pyenv init -)"' >> ~/.zshrc
    ```

    If you are a [Bash](https://www.gnu.org/software/bash/) user add this to your `~/.bashrc`:

    ```shell
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
    echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc
    ```

**tip**

    Run `pyenv doctor` to see if your environment is properly configured.

    
### Install Python 2.7.18


```shell
pyenv install 2.7.18
```

**tip**

    Run `pyenv versions` check installed versions


### Prepare a Python 2.x virtual environemnt

Prepare a Python 2.7 [virtualenv](https://virtualenv.pypa.io/en/latest) using the [pyenv-virtualenv](https://github.com/pyenv/pyenv-virtualenv) plugin:


``` shell
$ pyenv virtualenv 2.7.18 python2.7-senaite
```

Activate the virtual environment:

``` shell
$ pyenv activate python2.7-senaite

$ python -V
Python 2.7.18

$ which python
/home/senaite/.pyenv/shims/python
```


### Prepare the SENAITE AD/LDAP Plugin buildout environment

The `senaite.ldap` package contains a [Buildout](https://www.buildout.org/en/latest/) configuration that can be used to setup a fully working SENAITE environment.

**note**

    It is not possible to install `senaite.ldap` via [`pip`](https://pip.pypa.io/en/stable/)!


### Extract the contents of this package


``` shell
$ unzip senaite.ldap-1.0.0.zip
$ cd senaite.ldap-1.0.0
```

**info "Package Requirements"**
    
    ```
    sudo apt install unzip
    ```

### Install required Python dependencies

Install the dependencies

```
$ pip install -r requirements.txt
```

### Install system dependencies

SENAITE depends on several libraries that need to be installed on your system.

Here is an example on how to install these dependencies on a Debian system:

``` shell
$ sudo apt install libxml2 libxml2-dev libxslt1.1 libxslt1-dev libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 zlib1g
```


### Run Buildout

```shell
$ which buildout
senaite.ldap-1.0.0/python2.7/bin/buildout

$ buildout -c buildout.cfg
```


### Start your SENAITE instance and install SENAITE AD/LDAP Plugin

Run your new installed SENAITE instance in foreground mode:


```shell
$ bin/instance fg
```

This will start up a single SENAITE instance on http://localhost:8080:

``` shell
...
2024-10-11 10:51:06,987 INFO    [Zope:45][MainThread] Ready to handle requests
Starting server in PID 4481.
Serving on http://localhost:8080
```

**tip**

    You can hit `Ctrl+c` to stop the server


Opening this page will allow you to create a new SENAITE site in the database.


**note**

    Please install `senaite.ldap` via the [SENAITE Add-on controlpanel](http://localhost:8080/senaite/@@overview-controlpanel)


## How to setup the development version SENAITE LIMS

To test the compatibility of senaite.ldap with the latest
SENAITE sources, you can run the `development.cfg` configuration:

```shell
$ which buildout
senaite.ldap-1.0.0/python2.7/bin/buildout

$ buildout -c development.cfg
```

This will checkout the source distributions via [Git](https://git-scm.com) of
SENAITE and all the dependent add-ons into the `src` directory.

**important**

    Remember to run the migration steps via the [SENAITE Add-on controlpanel](http://localhost:8080/senaite/prefs_install_products_form) if upgrading an existing database!


### Run the contained tests

The add-on ships with a testing infrastructure to run automated tests.

You can run the tests from with the buildout directory:

```shell
$ bin/test
```


