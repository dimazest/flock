Introduction
============

Suppose we have a huge collection of tweets dedicated to some event, for example #brexit or Olympics. Clearly, we can't read them all to get in insight of what's going on. Can we extract computationally the a meaningful (graphical) summary?

The first idea is to apply doc2vec to the collection. The main goal is to get distributed representation of tweets, so later we could cluster them and see whether clusters are meaningful.

doc2vec takes as input labeled documents. In our case documents are tweets. Labeles can be anything, so I propse to have the following:

* tweet id, because the documents need to have a unique identifier
* hashtags
* user name of the author
* user mentions
* URLs that are in the tweet
  It ight be a good idea to split an url to several parts, so https://www.theguardian.com/travel/2016/aug/03/10-best-outdoor-swimming-holidays-around-world-italy-france-greece becomes:

  * the domain (www.theguardian.com)
  * the rest of the url, but split by / (travel, 2016, aug, 03, 10-best...)
* geo information, pobably as a sring (e.g. Berlin, Germany).
* creation time
  Possible formats are (we should have all of them):
  * %Y-%m-%d-%H
  * %Y-%m
  * %d to compare days
  * %H to compare hours
* language (from the tweet json object)
* named entities (from corenlp)

The good point is that we can also get a distributed representation of the labels, so we could in prinicple cluster hashtags, or compare websites.

Data sources
------------

Brexit
~~~~~~

*brexit* tweets about brexit. Fitering criteria: everything that contains the string "brexit".

Possible hypotheses:

* We should be able to see two groups of tweets: the ones that agains leaving the EU and the ones that are for.
* There should be corresponding hashtags.
* We might see general sentiment.
* Since we can retrieve named entities, we should be able to see polititians that belong to their camp.
* Since we have link information, we should be able to show what newsites are "for" and what are "against", or rather what's the user percepion of them.

Olympics
~~~~~~~~

*Olympic* tweets are the tweets that contain the string 'olympic' or are witten/mention the user @Olympics. Hopefully this data is more language diverse then brexit.

Hypotheses:

* We should be able to see clusters that correspond to different sports/athletes.

Latvia
~~~~~~

It would be nice to collect the tweets from Latvia. The main reason is that there is a large Russian minority. The goal is to contrast the Latvian minority with the Russian community and see what the interests of the two groups are, how they react to the events.

To link the tweets from two languages news articles might be useful. If we have an url of a Russian news item , it should be possible to retrieve a similar Latvian article.

Hypotheses:
  * Two distinc users. The distinction is based on the ethnical backgound.
  * Various/similar interests? Do the groups listen to same artists, watch same movies, etc.
  * What are the most discussed topics and are they percieved differently? E.g. brexit might have been percieved equally along the groups, but the attitute to Ukrain might vary.

Data collection. Include twitter accounts fo the main media entities, politicians, artists(?). Collect the data from the largest cities. See the most popular users and track them.
