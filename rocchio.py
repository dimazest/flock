import pandas as pd
import seaborn as sns

def read_qrels(fname, name):
    if name == 'NIST':
        names = ['Topic', 'q0', 'tweet_id', 'judgment']
    else:
        names = ['Topic', 'user', 'tweet_id', 'judgment', 'timestamp']
    qrels = pd.read_csv(
        fname,
        sep='\s+',
        names=names,
        usecols=['Topic', 'tweet_id', 'judgment'],
        header=None,
        index_col=['tweet_id', 'Topic'],
        squeeze=True,
    )

    qrels = qrels[qrels >= 0]

    qrels.name = name
    
    return qrels


def read_point(fname, prefix='eval/RTS17/gundog/point/'):
    point = pd.read_csv(
        prefix+fname,
        names=[
            'Topic', 'tweet_id',
            'Distance to query',
            'Distance to positive', 'Distance to negative',
            'Score',
            'retrieve', 'Possible feedback',
            'Positive', 'Negative',
            'Time', 'retrieved_count'
        ],
        header=None,
        parse_dates=['Time'],
        low_memory=False,
    )#.dropna()

    point.sort_values(by=['Time', 'tweet_id', 'Topic'], inplace=True)

    point.drop_duplicates(subset=['tweet_id', 'Topic'], inplace=True)
    point.set_index(
        [
            'Time',
            'tweet_id', 'Topic',
        ],
        inplace=True,
    )
    
    point['Score'].clip(lower=0, upper=2, inplace=True)

    return point


def plot_feedback(point, title=None, ax=None):
    return (
        point[['Positive', 'Negative']]
        .unstack('Topic', fill_value=0)
        .cummax()
        .groupby(axis='columns', level=0).mean()
        .reset_index('tweet_id', drop=True).plot(title=title, ax=ax)
    )


def evaluate(point, qrels, query_threshold=0.8):
    evaluation = point[['Distance to query', 'Score', 'retrieve']].reset_index('Time', drop=True)

    evaluation['retrieve_query'] = evaluation['Distance to query'] < query_threshold
    evaluation['relevant'] = qrels[evaluation.index] > 0

    __ = {
        (True, True, True): 'Correct',
        (True, True, False): 'Wrong',
        (False, False, True): 'Wrong',
        (False, False, False): 'Correct',        

        (True, False, True): 'ScoreTN',
        (True, False, False): 'ScoreFN',
        (False, True, True): 'ScoreTP',
        (False, True, False): 'ScoreFP',
    }

    evaluation['Evaluation'] = evaluation.apply(
        lambda r: __.get(tuple(r.loc[['retrieve_query', 'retrieve', 'relevant']].values)),
        axis='columns',
    )
    
    evaluation.reset_index('Topic', inplace=True)
    
    return evaluation


def plot_evaluation(evaluation, topics=None):
    if topics is None:
        topics = [
            'RTS114', 'RTS113',
            'RTS167', 'RTS190',
            'RTS73', 'RTS136',
    #         'RTS207', 'RTS204', # TOP: TN, FN
    #         'RTS219', 'RTS94', # TOP: TP, FP
    # #         'RTS94', 'RTS204',
    #         'RTS212', 'RTS48', # FINA, Panera Bread
        ]
    return sns.lmplot(
        data=evaluation,
        x='Distance to query', y='Score',
        hue='Evaluation',
        hue_order=[
            'Correct', 'Wrong',
            'ScoreTP', 'ScoreFP', # LR
            'ScoreTN', 'ScoreFN', # UL
        ],
        markers=[
            '.', '.',
            '+', '+',
            'x', 'x',
        ],
        palette = {
            'Correct': 'tab:green', 'Wrong': 'tab:red',
            'Relevant': 'tab:green', 'Non-relevant': 'tab:red',
            'ScoreTP': 'tab:green', 'ScoreFP': 'tab:red', # LR
            'ScoreTN': 'tab:green', 'ScoreFN': 'tab:red', # UL
        },
        col='Topic',
        col_order=topics,
        col_wrap=2,
        ci=None,
        sharex=True,
        sharey=True,
        fit_reg=False,
    )
