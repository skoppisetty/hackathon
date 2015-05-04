=====================================
iDigBio Data Ingestion Tool Packaging
=====================================

The build script is currently only for Mac OS X and Windows. To execute it, just
cd into the proper directory and run::
    
    python build.py

When run on Windows, an exe is built. When run on Mac OS X, a .app bundle and a
dmg (for distribution) are built.

Prior Windows Setup
-------------------

On Windows, you'll need to install Python 2.7 from python.org_ (we used 2.7.3),
and cx_Freeze_.

You need to download and install pyexiv2 from
http://tilloy.net/dev/pyexiv2/download.html.

Prior OS X Setup
----------------

Install Python 2.7 (we used 2.7.3) from python.org_ (the built-in OS X verion,
and the version from macports will **not** work), and then install setuptools
for it::
    
    curl http://pypi.python.org/packages/2.7/s/setuptools/setuptools-0.6c11-py2.7.egg > setuptools-0.6c11-py2.7.egg
    sudo sh setuptools-0.6c11-py2.7.egg
    rm setuptools-0.6c11-py2.7.egg
    sudo easy_install-2.7 py2app

The pyexiv2 packet for Mac is only available in brew.

1. You need to install brew by following: http://brew.sh/

2. Install pyexiv2 from brew (Note it may take very looong time because it's going to install dependencies including boost)::

   brew install pyexiv2

32-Bit vs 64-Bit
----------------

A 32-bit application can execute on a 64-bit system, but not vice-versa, so we
should distribute 32-bit versions of our software primarily.

Because cx_Freeze and py2app copy in the system-wide version of Python, you must
ensure that you are building everything with 32-bit copies of Python. The OS
doesn't need to be 32-bit, but all the dependencies should be in 32-bit form.

If you are unsure about compatibility on OS X, you can force it to boot with a
`32-bit kernel`_. When building with Windows you can test with a 32-bit version
of the OS.

.. _python.org: http://python.org/
.. _cx_Freeze: http://cx-freeze.sourceforge.net/
.. _32-bit kernel: https://support.apple.com/kb/HT3773
