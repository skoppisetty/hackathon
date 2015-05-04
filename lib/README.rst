Organization of Dependent Libraries
===================================

The iDigBio data ingestion tool has a few dependencies, all of which are
pure-python (platform independent) and are included in this directory:

Jinja 2.6
    A popular templating engine.
CherryPy 3.2.2
    A lightweight Python webserver library. The current included version is
    3.2.2.
SqlAlchemy 0.7.7
    A popular Python Object Relational Mapper used for interfacing with sqlite3.
appdirs 1.2.0
    A small Python module for determining appropriate platform-specific dirs,
    e.g. a "user data dir".
poster 0.8.1
    A small Python library that allows for streaming HTTP uploads and
    multipart/form-data encoding.

The iDigBio ingestion tool is currently intended to run on Python 2.7.

Updating Packages
-----------------

Each package was individually downloaded from the respective websites,
extracted, and the relevant folder was placed in this directory. Extracting
allows git to treat the files as text rather than binary blobs, compressing
things better when packages inevitably get upgraded. Upon execution, the
software modifies ``sys.path`` include this directory. If you would like to
update a version of a dependency used, you should simply replace the version in
this directory.
