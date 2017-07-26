import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

import flask_login

from flock.model import Base
from flock import model


class User(Base, flask_login.UserMixin):
    __tablename__ = 'user'
    __table_args__ = (
        sa.UniqueConstraint('first_name', 'last_name'),
    )

    id = sa.Column(sa.Integer, primary_key=True)

    first_name = sa.Column(sa.String(50), nullable=False)
    last_name = sa.Column(sa.String(50), nullable=False)

    def is_active(self):
        return True


class Topic(Base):
    __tablename__ = 'topic'

    id = sa.Column(sa.Integer, primary_key=True)

    title = sa.Column(sa.String(500), nullable=False)
    description = sa.Column(sa.String(1000), nullable=True)
    narrative = sa.Column(sa.String(1000), nullable=True)

    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    user = sa.orm.relationship('User', backref='topics')

    questionnaire = sa.orm.relationship('TopicQuestionnaire', uselist=False)

    def judgment_count(self, value):
        return len([j for j in self.judgments if j.judgment == value])


class EvalTopic(Base):
    __tablename__ = 'eval_topic'

    rts_id = sa.Column(sa.String(10), primary_key=True)
    collection = sa.Column(sa.String(100), primary_key=True)

    title = sa.Column(sa.String(500), nullable=False)

    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    user = sa.orm.relationship('User', backref='eval_topics')

    def tweet_count(self, judged_only=False):
        return len([j for j in self.judgments if not judged_only or j.judgment is not None])

    def relevant_count(self):
        return len([j for j in self.judgments if j.judgment and j.judgment > 0])

    def clustered_count(self):
        return len([1 for c in self.clusters for a in c.assignments])

    def tweet_by_id(self, relevant_only=False):
        session = sa.inspect(self).session

        tweet_by_id = {
            j.tweet_id: model.Tweet(
                    tweet_id=j.tweet_id,
                    features={
                        'repr': {
                            'text': 'MISSING: {}'.format(j.tweet_id),
                            'user__screen_name': 'Unknown',
                            'user__name': 'unknown',
                        },
                    },
                    created_at='unknown',
                )
            for j in self.judgments
            if not relevant_only or j.judgment > 0
        }

        for tweet in (
                session.query(model.Tweet)
                .filter(
                    model.Tweet.collection == self.collection,
                    model.Tweet.tweet_id.in_(tweet_by_id.keys()),
                )

        ):
            tweet_by_id[tweet.tweet_id] = tweet

        return tweet_by_id

    def state(self):
        tweet_by_id = self.tweet_by_id(relevant_only=True)

        def tweet_to_json(tweets):
            return [
                {
                    'id': str(t.tweet_id),
                    'text': t.features['repr']['text'],
                    'screen_name': t.features['repr']['user__screen_name'],
                    'user_name': t.features['repr']['user__name'],
                    'created_at': t.created_at,
                }
                for t in tweets
            ]

        tweets = {}
        for cluster in self.clusters:
            tweets[cluster.rts_id] = tweet_to_json(tweet_by_id.pop(a.tweet_id) for a in cluster.assignments)

        unassigned_tweets = tweet_to_json(tweet_by_id.values())

        state = {
            'clusters': sorted(
                (
                    {
                        'id': c.rts_id,
                        'gloss': c.gloss,
                        'size': len(tweets[c.rts_id])
                    }
                    for c in self.clusters
                ),
                key=lambda c: c['id'],
                reverse=True,
            ),
            'tweets': tweets,
            'unassignedTweets': unassigned_tweets,
            'topic': {
                'title': self.title,
                'id': self.rts_id,
            },
        }

        return state


class EvalRelevanceJudgment(Base):
    __tablename__ = 'eval_relevance_judgment'
    __table_args__ = (
        sa.ForeignKeyConstraint(['eval_topic_rts_id', 'collection'], ['eval_topic.rts_id', 'eval_topic.collection']),
    )

    eval_topic_rts_id = sa.Column(sa.String,  primary_key=True)
    collection = sa.Column(sa.String, primary_key=True)

    tweet_id = sa.Column(
        sa.BigInteger,
        # sa.ForeignKey('tweet.tweet_id'),
        primary_key=True,
    )

    judgment = sa.Column(sa.Integer, nullable=True)

    eval_topic = sa.orm.relationship('EvalTopic', backref='judgments')


class EvalCluster(Base):
    __tablename__ = 'eval_cluster'
    __table_args__ = (
            sa.ForeignKeyConstraint(['eval_topic_rts_id', 'eval_topic_collection'], ['eval_topic.rts_id', 'eval_topic.collection']),
    )

    eval_topic_rts_id = sa.Column(sa.String, primary_key=True)
    eval_topic_collection = sa.Column(sa.String, primary_key=True)
    rts_id = sa.Column(sa.Integer, sa.Sequence('eval_cluster__rts_id'), primary_key=True)

    gloss = sa.Column(sa.String, nullable=False)

    eval_topic = sa.orm.relationship('EvalTopic', backref='clusters')


class EvalClusterAssignment(Base):
    __tablename__ = 'eval_cluster_assignment'
    __table_args__ = (
        sa.ForeignKeyConstraint(
            ['eval_topic_rts_id', 'eval_topic_collection', 'eval_cluster_rts_id'],
            ['eval_cluster.eval_topic_rts_id', 'eval_cluster.eval_topic_collection', 'eval_cluster.rts_id'],
        ),
    )

    eval_topic_rts_id = sa.Column(sa.String, primary_key=True)
    eval_topic_collection = sa.Column(sa.String, primary_key=True)
    # Ideally, it should point to EvalRelevanceJudgment.
    tweet_id = sa.Column(
        sa.BigInteger,
        # sa.ForeignKey('tweet.tweet_id'),
        primary_key=True
    )

    eval_cluster_rts_id = sa.Column(sa.Integer)

    eval_cluster = sa.orm.relationship('EvalCluster', backref='assignments')


class TopicQuery(Base):
    __tablename__ = 'topic_query'
    __table_args__ = (
        sa.UniqueConstraint('query', 'filter', 'filter_args', 'cluster', 'topic_id'),
    )

    id = sa.Column(sa.Integer, primary_key=True)

    query = sa.Column(sa.String)
    filter = sa.Column(sa.String)
    filter_args = sa.Column(pg.JSONB)
    cluster = sa.Column(sa.String)

    topic_id = sa.Column(sa.Integer, sa.ForeignKey('topic.id'), nullable=False)
    topic = sa.orm.relationship('Topic', backref='queries')

    @property
    def filter_args_dict(self):
        return dict(self.filter_args) if self.filter_args is not None else {}


class TopicQuestionnaire(Base):
    __tablename__ = 'topic_questionnaire'

    topic_id = sa.Column(sa.Integer, sa.ForeignKey('topic.id'), nullable=False, primary_key=True)
    topic = sa.orm.relationship('Topic')

    answer = sa.Column(pg.JSONB)


class RelevanceJudgment(Base):
    __tablename__ = 'relevance_judgment'

    topic_id = sa.Column(sa.Integer, sa.ForeignKey('topic.id'), nullable=False, primary_key=True)
    topic = sa.orm.relationship('Topic', backref='judgments')

    tweet_id = sa.Column(
        sa.BigInteger,
        # sa.ForeignKey('tweet.tweet_id'),
        nullable=False,
        primary_key=True,
    )

    judgment = sa.Column(sa.Integer, nullable=False)


class TaskResult(Base):
    __tablename__ = 'task_result'
    __table_args__ = (
        sa.UniqueConstraint('name', 'args', 'kwargs'),
    )

    _id = sa.Column(sa.Integer, primary_key=True)
    celery_id = sa.Column(sa.String, unique=True)
    celery_status = sa.Column(sa.String)

    name = sa.Column(sa.String, nullable=False)
    args = sa.Column(pg.JSONB)
    kwargs = sa.Column(pg.JSONB)
    result = sa.Column(pg.JSONB)


class UserAction(Base):
    __tablename__ = 'user_action'

    id = sa.Column(sa.Integer, primary_key=True)

    timestamp = sa.Column(sa.DateTime, default=sa.func.now())
    user_id = sa.Column(sa.Integer, sa.ForeignKey('user.id'), nullable=False)
    user = sa.orm.relationship('User', backref='actions')

    url = sa.Column(sa.String(1000))
    endpoint = sa.Column(sa.String(100))
    view_args = sa.Column(pg.JSONB)
    collection = sa.Column(sa.String(100))
    request_args = sa.Column(pg.JSONB)
    request_form = sa.Column(pg.JSONB)
    headers = sa.Column(pg.JSONB)
