# Flock

# Setup

Initial setup: get the source and dependencies

``` bash

# Get the sources
git clone git@github.com:dimazest/flock.git
cd flock
git co -b eval origin/eval


# Create a Python envinroment with Conda
~/miniconda3/bin/conda create -n flock-udel python=3.6
. ~/miniconda3/bin/activate flock-udel  # activate it

# Add the conda-forge repo
conda config --add channels conda-forge

# Install some dependencies, check [sysegg] in boostrap.cfg
conda install psycopg2 pyzmq psutil gensim numpy scikit-learn scipy

# Bootstrap and initially deploy the project
python bootstrap-buildout.py
bin/buildout
```

Optional, get PostgreSQL up and running

```bash
# Optional, in a separate tab

# Activate the envinroment
. ~/miniconda3/bin/activate flock-udel

# Install PostgreSQL
conda install postgresql

# Initialize the DB
initdb -D pgdata

# Start the server
pg_ctl -D pgdata/ start

# Create the database
createdb twitter

# Optional, check the connection
psql -d twitter  # it should give a PostgreSQL command shell.
```

Init the DB
```bash

bin/flock initdb
bin/flock-web initdb


```

# Copyright notice

Government Legal

This software was produced by NIST, an agency of the U.S. government, and by statute is not subject to copyright in the United States.
Recipients of this software assume all responsibilities associated with its operation, modification and maintenance.
~/miniconda3/bin/conda create -n flock-udel python=3.6
