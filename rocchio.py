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
    )

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
        .groupby(axis='columns', level=0).sum()
        .reset_index('tweet_id', drop=True).plot(title=title, ax=ax)
    )


def evaluate(point, qrels, query_threshold=0.8):
    evaluation = point[['Distance to query', 'Score', 'retrieve']].reset_index('Time', drop=False)

    evaluation['retrieve_query'] = evaluation['Distance to query'] < query_threshold

    qrels_evalueation = qrels[evaluation.index]
    mask = qrels_evalueation.isna().values
    evaluation['relevant'] = qrels_evalueation > 0
    evaluation.loc[mask, 'relevant'] = None
    
    q = evaluation['retrieve_query']
    r = evaluation['retrieve']
    P = evaluation['relevant'].notna()
    R = evaluation['relevant'] == 1
    evaluation.loc[P & (~q & ~r & ~R), 'Evaluation'] = 'TN'
    evaluation.loc[P & (q & r & R), 'Evaluation'] = 'TP'
    evaluation.loc[P & (~q & ~r & R), 'Evaluation'] = 'FN'
    evaluation.loc[P & (q & r & ~R), 'Evaluation'] = 'FP'
    
    evaluation.loc[P & (~q & r & ~R), 'Evaluation'] = 'ScoreFP'
    evaluation.loc[P & (q & ~r & R), 'Evaluation'] = 'ScoreFN'
    evaluation.loc[P & (~q & r & R), 'Evaluation'] = 'ScoreTP'
    evaluation.loc[P & (q & ~r & ~R), 'Evaluation'] = 'ScoreTN'
    
    evaluation.loc[~P, 'Evaluation'] = 'Not evaluated'
    
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
        data=evaluation.reset_index('Topic'),
        x='Distance to query', y='Score',
        hue='Evaluation',
        hue_order=[
            'TP', 'TN',
            'FP', 'FN',
            'ScoreTP', 'ScoreFP', # LR
            'ScoreTN', 'ScoreFN', # UL
        ],
        markers=[
            '.', '.',
            '.', '.',
            '+', '+',
            'x', 'x',
        ],
        palette = {
            'TP': 'tab:green', 'FP': 'tab:red',
            'TN': 'tab:green', 'FN': 'tab:red',
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

def evaluation_over_time(evaluation, title=None, logy=True, ax=None):
    _ = evaluation[['Time', 'Evaluation']]

    _ = _.groupby('Evaluation').apply(lambda g: g.resample('1h', on='Time').size())
    _ = _.unstack('Evaluation', fill_value=0)

#     _.set_index('Time', inplace=True)

#     _ = _['Evaluation']

#     _ = _.groupby(level='Time').apply(lambda g: g.value_counts())
#     _ = _.groupby(level=1).resample('1h', level='Time').sum().unstack(0, fill_value=0).fillna(0)

#     #     _ = _.unstack(1, fill_value=0).resample('1h').sum().fillna(0)
    
    _ = _.cumsum()

#     _.plot(logy=logy, title=title, ax=ax, sharey=True, sharex=True)
    
    return _