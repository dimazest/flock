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

# You should have these envinroment variables set. They should be Twitter
# credentials.
# export ACCESS_TOKEN="..."
# export ACCESS_TOKEN_SECRET="..."
# export CONSUMER_KEY="..."
# export CONSUMER_SECRET="..."
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

Generate Javascript frontend
```bash
# In a separate tab
. ~/miniconda3/bin/activate flock-udel

# Install yarn and npm
conda install yarn

cd flock-web

# Install webpack
npm install webpack

# Create a bundle.js
node_modules/webpack/bin/webpack.js

# During development, watch for the changes, so the .js files are regenerated
node_modules/webpack/bin/webpack.js -w
```

Start the backend
```bash
# In a separate tab, start the circus deamon. It will take care of running processes
bin/circusd parts/etc/circus.ini

# In another separate tab, start circusctl, a client to circusd
bin/circusctl
(circusctl) start flock-web  # Start flock-web, the main backend process

# You are ready to open http://localhost:8080, but insert data first.
# If you want to access the web backend from a remote machine, you will
# either need to:
#
# * open port 8080 (or rather set up a rverse proxy)
# * ssh -L8080:localhost:8080 $HOST
```

Insert the data
```bash
# Create a folder to track inserted pools
mkdir rts/17/pools-inserted

# Process the qurels file
# It will create a user with firstname 'Dmitrijs' and lastname 'hi'.
bin/python src/produce/produce rts/17/qrels-sorted.inserted

# Insert topic metadata
bin/python src/produce/produce rts/17/topics.json.inserted
```

Now you are ready to open http://localhost:8080, after logging in (Dmitrijs, hi), you should be redirected to http://localhost:8080/c/RTS17/eval/topics

# Copyright notice

Government Legal

This software was produced by NIST, an agency of the U.S. government, and by statute is not subject to copyright in the United States.
Recipients of this software assume all responsibilities associated with its operation, modification and maintenance.
