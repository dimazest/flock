Introduction
============

Suppose we have a huge collection of tweets dedicated to some event, for example #brexit or Olympics. Clearly, we can't read them all to get in insight of what's going on. Can we extract computationally the a meaningful (graphical) summary?

The first idea is to apply doc2vec to the collection. The main goal is to get distributed representation of tweets, so later we could cluster them and see whether clusters are meaningful.

doc2vec takes as input labeled documents. In our case documents are tweets. Labeles can be anything, so I propse to have the following:

* tweet id, because the documents need to have a unique identifier
* hashtags
* user
* user mentions
* URLs that are in the tweet
  It ight be a good idea to split an url to several parts, so https://www.theguardian.com/travel/2016/aug/03/10-best-outdoor-swimming-holidays-around-world-italy-france-greece becomes:

  * the domain (www.theguardian.com)
  * the rest of the url, but split by / (travel, 2016, aug, 03, 10-best...)
  
* creation time
* language (from the tweet json object)
* named entities (from corenlp)

The good point is that we can also get a distributed representation of the labels, so we could in prinicple cluster hashtags, or compare websites.