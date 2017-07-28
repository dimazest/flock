import 'babel-polyfill'

import React from 'react'
import { render } from 'react-dom'
import { Provider } from 'react-redux'
import { createStore, applyMiddleware } from 'redux'
import thunkMiddleware from 'redux-thunk'
import { createLogger } from 'redux-logger'

/* Helpers */

function tweetCluster(tweets, clusterID) {
    return tweets[clusterID] || []
}

function clusterNewName(tweets, clusterID){
    const tw = tweetCluster(tweets, clusterID)

    return tw.length > 0 ? tw[0].text : ''
}

function clusterFirstTweetID(tweets, clusterID) {
    const tw = tweetCluster(tweets, clusterID)

    return tw.length > 0 ? tw[0].id : null
}

/* Actions */

const REQUEST_ADD_CLUSTER = 'REQUEST_ADD_CLUSTER'
function requestAddCluster(gloss){
    return {
        type: REQUEST_ADD_CLUSTER,
        gloss,
    }
}

const RECEIVE_BACKEND = 'RECEIVE_BACKEND'
function receiveBackend(backend){
    backend = {
        ...backend,
        tweets: {
            ...backend.tweets,
            null: backend.unassignedTweets,
        },
    }

    return {
        type: RECEIVE_BACKEND,
        backend,
    }
}

function addCluster(gloss) {
    return dispatch => {
        dispatch(requestAddCluster(gloss))

        return fetch(
            window.ADD_CLUSTER_URL,
            {
                credentials: 'include',
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({gloss})
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured.', error)
            )
            .then(
                json => {
                    dispatch(receiveBackend(json))
                    dispatch(activateCluster(json.newClusterID))
                }
            )
    }
}

const REQUEST_ASSIGN_TWEET = 'REQUEST_ASSIGN_TWEET'
function requestAssignTweet(tweet_id, cluster_id) {
    console.log(`Request assign tweet ${tweet_id} to cluster ${cluster_id}`)

    return {
        type: REQUEST_ASSIGN_TWEET,
        tweet_id,
        cluster_id,
    }
}

function assignTweet(tweet_id, cluster_id) {
    return dispatch => {
        dispatch(requestAssignTweet(tweet_id, cluster_id))

        dispatch(activateTweet(tweet_id))
        dispatch(activateCluster(cluster_id))

        if (tweet_id === null | cluster_id === null) {
            console.log('Either tweet_id or cluster_id are missing.')
            return
        }

        return fetch(
            window.ASSIGN_TWEET_TO_CLUSTER_URL,
            {
                credentials: 'include',
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({tweet_id, cluster_id})
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured', error)
            )
            .then(
                json => {
                    dispatch(receiveBackend(json))
                }
            )
    }
}

const ACTIVATE_TWEET = 'ACTIVATE_TWEET'
function activateTweet(tweet_id){
    return {
        type: ACTIVATE_TWEET,
        tweet_id,
    }
}

const ACTIVATE_CLUSTER = 'ACTIVATE_CLUSTER'
function activateCluster(activeClusterID){
    return {
        type: ACTIVATE_CLUSTER,
        activeClusterID,
    }
}

const SHOW_CLUSTER = 'SHOW_CLUSTER'
function showCluster(visibleClusterID){
    return {
        type: SHOW_CLUSTER,
        visibleClusterID,
    }
}

const CHANGE_NEW_CLUSTER_NAME = 'CHANGE_NEW_CLUSTER_NAME'
function chnageNewClusterName(newClusterName){
    return {
        type: CHANGE_NEW_CLUSTER_NAME,
        newClusterName,
    }
}

const SHOW_MORE_JUDGMENT_TWEETS = 'SHOW_MORE_JUDGMENT_TWEETS'
function showMoreJudgmentTweets(){
    return {type: SHOW_MORE_JUDGMENT_TWEETS}
}


const REQUEST_JUDGE_TWEET = 'REQUEST_JUDGE_TWEET'
function requestJudgeTweet(tweet_id, judgment){
    console.log(`Judge tweet ${tweet_id}: ${judgment}`)

    return {
        type: REQUEST_JUDGE_TWEET,
        tweet_id,
        judgment,
    }
}

const RECEIVE_TWEETS_AND_JUDGMENTS = 'RECEIVE_TWEETS_AND_JUDGMENTS'
function receiveTweetsAndJudgments(tweetsAndJudgments) {
    return {
        type: RECEIVE_TWEETS_AND_JUDGMENTS,
        tweetsAndJudgments
    }
}

const FILTER_TWEETS = 'FILTER_TWEETS'
function filterTweets(judgment) {
    return {
        type: FILTER_TWEETS,
        judgment,
    }
}

function judgeTweet(tweet_id, judgment){
    return dispatch => {
        dispatch(requestJudgeTweet(tweet_id, judgment))

        return fetch(
            window.JUDGE_TWEET_URL,
            {
                credentials: 'include',
                method: 'POST',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({tweet_id, judgment})
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured', error)
            )
            .then(
                json => {
                    dispatch(receiveTweetsAndJudgments(json))
                }
            )
    }
}

/* Components */

import { connect } from 'react-redux'
import PropTypes from 'prop-types'

let TopicInfo= ({ topic, full=true}) => (
    <div>
        <h1>Evaluation topic {topic.title}</h1>
        {full &&
         <div>
             {(topic.title !== null) &&
              <div className="row form-group">
                  <label className="col-2 col-form-label">Title</label>
                  <div className="col">
                      <input className="form-control" type="text" value={topic.title} disabled={true}/>
                  </div>
              </div>
             }
             {(topic.description !== null) &&
              <div className="row form-group">
                  <label className="col-2 col-form-label">Description</label>
                  <div className="col">
                      <input className="form-control" value={topic.description} disabled={true}/>
                  </div>
              </div>
             }
             {(topic.narrative !== null) &&
              <div className="row form-group">
                  <label className="col-2 col-form-label">Narrative</label>
                  <div className="col">
                      <textarea className="form-control" type="text" value={topic.narrative} disabled={true}/>
                  </div>
              </div>
             }
         </div>
        }
    </div>
)
TopicInfo = connect(state => ({topic: state.backend.topic}))(TopicInfo)

let AddCluster = ({tweets, visibleClusterID, newClusterName, dispatch }) => {
    let input

    return (
        <div className="mb-4">
            <form
                onSubmit={
                    e => {
                        e.preventDefault()
                        if (!newClusterName.trim()) {
                            return
                        }
                        dispatch(addCluster(newClusterName))
                    }
                }
            >
                <div className="row">
                    <div className="col">
                        <input
                            type="text"
                            className="form-control"
                            placeholder="Cluster gloss"
                            ref={node => {
                                    input = node
                            }}
                            value={newClusterName}
                            onChange={
                                e => {
                                    dispatch(chnageNewClusterName(e.target.value))
                                }
                            }
                        />
                    </div>
                    <div className="col-2" style={{minWidth: "164px"}}>
                        <button className="btn btn-outline-success my-2 my-sm-0 w-100" type="submit">
                            Add Cluster
                        </button>
                    </div>
                </div>
            </form>
        </div>
    )
}
AddCluster = connect(
    state => (
        {
            tweets: state.backend.tweets,
            visibleClusterID: state.frontend.visibleClusterID,
            newClusterName: state.frontend.newClusterName,
        }
    )
)(AddCluster)

const Cluster = ({ onActivateClick, onActivateAndAssignClick, onShowClick, gloss, size, active=false, visible=false }) => (
    <li
        className={"list-group-item " + (active ? "active " : "")}
    >
        <div className="col">{gloss}</div>
        <div className="btn-group col-9 col-lg-6 justify-content-end" style={{minWidth: "453px"}}>
            <button className="btn btn-warning" onClick={e => {e.stopPropagation(); }}>Rename</button>
            <button className="btn btn-danger" onClick={e => {e.stopPropagation(); }}>Delete</button>
            <button className="btn btn-info"
                    onClick={
                        e => {
                            e.stopPropagation()
                            onShowClick()
                        }
                    }
            >
                {visible ? "Show Unclustered" : `Show (${size})`}
            </button>
            <button className={"btn btn-secondary " + (active ? "active" : "")} onClick={e => {e.stopPropagation(); onActivateClick()}}>Select</button>
            <button className="btn btn-primary" onClick={onActivateAndAssignClick}>Assign</button>
        </div>
    </li>
)
Cluster.propTypes = {
    onActivateClick: PropTypes.func.isRequired,
    onActivateAndAssignClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired,
    gloss: PropTypes.string.isRequired,
    size: PropTypes.number.isRequired,
    active: PropTypes.bool,
    visible: PropTypes.bool
}

let ClusterList = ({ clusters, activeClusterID, activeTweetID, visibleClusterID, onActivateClick, onActivateAndAssignClick, onShowClick }) => (
    <div style={{overflowY: 'scroll', maxHeight: '90%'}}>
        <ul className="list-group">
            {
                clusters.map(
                    cluster => (
                        <Cluster key={cluster.id} gloss={cluster.gloss} size={cluster.size}
                                 onActivateClick={() => onActivateClick(cluster.id)}
                                 onActivateAndAssignClick={() => onActivateAndAssignClick(activeTweetID, cluster.id)}
                                 active={cluster.id === activeClusterID}
                                 onShowClick={() => onShowClick(cluster.id)}
                                 visible={cluster.id === visibleClusterID}
                        />
                    )
                )
            }
        </ul>
    </div>
)
ClusterList.propTypes = {
    clusters: PropTypes.arrayOf(
        PropTypes.shape(
            {
                id: PropTypes.number.isRequired,
                gloss: PropTypes.string.isRequired
            }
        ).isRequired
    ).isRequired,
    activeClusterID: PropTypes.number,
    activeTweetID: PropTypes.string,
    visibleClusterID: PropTypes.number,
    onActivateClick: PropTypes.func.isRequired,
    onActivateAndAssignClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired
}

ClusterList = connect(
    state => (
        {
            clusters: state.backend.clusters,
            activeClusterID: state.frontend.activeClusterID,
            activeTweetID: state.frontend.activeTweetID,
            visibleClusterID: state.frontend.visibleClusterID,

        }
    ),
    dispatch => (
        {
            onActivateClick: activeClusterID => {dispatch(activateCluster(activeClusterID))},
            onActivateAndAssignClick: (activeTweetID, activeClusterID) => {dispatch(assignTweet(activeTweetID, activeClusterID))},
            onShowClick: id => {dispatch(showCluster(id))},
        }
    )
)(ClusterList)

import TweetEmbed from './tweet-embed'
/* import TweetEmbed from 'react-tweet-embed'*/

const ClusteredTweet = ({ tweet, onAssignClick, active }) => (
    <div className="row" key={tweet.id}>
        <div className="col-1" style={{margin: '10px'}}>
            <button className={"btn " +  (active ? "btn-primary " : "btn-outline-primary ")} style={{height: '100%'}} onClick={onAssignClick}>Assign</button>
        </div>
        <div className="col ml-1">
            <TweetEmbed{...tweet} />
        </div>
    </div>
)
ClusteredTweet.propTypes = {
    tweet: PropTypes.object.isRequired,
    onAssignClick: PropTypes.func,
    active: PropTypes.bool,
}

let TweetList = ({ tweets, onAssignClick, visibleClusterID=null, activeClusterID=null, activeTweetID=null }) => {

    const tweetsForCluster = tweetCluster(tweets, visibleClusterID)

    if (!tweetsForCluster.length) {
        if (visibleClusterID === null) {
            return <div className={`alert alert-success`} role="alert">
                <strong>{`All tweets are assigned to a cluster.`}</strong> <a href={window.TOPICS_URL} className="alert-link">Show the topic list.</a>
            </div>
        } else {
            return <div className={`alert alert-warning`} role="alert"><strong>{`No tweets are assigned to this cluster.`}</strong></div>
        }
    }

    return <div>
        {tweetsForCluster.map(tweet => (
            <ClusteredTweet
                key={tweet.id}
                tweet={tweet}
                onAssignClick={() => onAssignClick(tweet.id, activeClusterID)}
                active={tweet.id === activeTweetID}
            />
        ))}
    </div>
}
TweetList.propTypes = {
    tweets: PropTypes.objectOf(PropTypes.array),
    onAssignClick: PropTypes.func.isRequired,
    visibleClusterID: PropTypes.number,
    activeClusterID: PropTypes.number,
    activeTweetID: PropTypes.string,
}

TweetList = connect(
    state => (
        {
            tweets: state.backend.tweets,
            visibleClusterID: state.frontend.visibleClusterID,
            activeClusterID: state.frontend.activeClusterID,
            activeTweetID: state.frontend.activeTweetID,
        }
    ),
    dispatch => (
        {
            onAssignClick: (tweet_id, activeClusterID) => {dispatch(assignTweet(tweet_id, activeClusterID))}
        }
    ),
)(TweetList)

function tweetClusterApp(state={}, action) {
    switch (action.type) {
        case RECEIVE_BACKEND:
            return {
                ...state,
                backend: action.backend,
                frontend: {
                    ...state.frontend,
                    activeTweetID: clusterFirstTweetID(action.backend.tweets, state.frontend.visibleClusterID),
                    newClusterName: clusterNewName(action.backend.tweets, state.frontend.visibleClusterID),
                }
            }
        case ACTIVATE_CLUSTER:
            const activeClusterID = action.activeClusterID === state.frontend.activeClusterID ? null : action.activeClusterID
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    activeClusterID: activeClusterID,
                },
            }
        case ACTIVATE_TWEET:
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    activeTweetID: action.tweet_id,
                }
            }
        case SHOW_CLUSTER: {
            const visibleClusterID = action.visibleClusterID === state.frontend.visibleClusterID ? null : action.visibleClusterID
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    visibleClusterID: visibleClusterID,
                    activeTweetID: clusterFirstTweetID(state.backend.tweets, visibleClusterID),
                    newClusterName: clusterNewName(state.backend.tweets, visibleClusterID),
                },
            }
        }
        case CHANGE_NEW_CLUSTER_NAME:{
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    newClusterName: action.newClusterName,
                },
            }
        }
        default:
            return state
    }
}

const ClusterApp = () => (
    <div className="row">
        <div className="col-6 bg-faded sidebar bd-links">
            <TopicInfo full={false}/>
            <AddCluster />
            <ClusterList />
        </div>
        <main className="col offset-6">
            <TweetList />
        </main>
    </div>
)


window.cluster = () => {
    window.initialState = {
        'backend': {
            ...window.BACKEND,
            tweets: {
                ...window.BACKEND.tweets,
                null: window.BACKEND.unassignedTweets,
            },
        },
        'frontend': {
            activeClusterID: null,
            activeTweetID: clusterFirstTweetID({null: window.BACKEND.unassignedTweets}, null),
            visibleClusterID: null,
            newClusterName: clusterNewName({null: window.BACKEND.unassignedTweets}, null),
        }
    }

    let store = createStore(
        tweetClusterApp,
        window.initialState,
        applyMiddleware(thunkMiddleware, createLogger()),
    )
    window.store = store;

    render(
        <Provider store={store}>
            <ClusterApp />
        </Provider>,
        document.getElementById('main-content')
    )
}

function tweetJudgeApp(state={}, action) {
    switch (action.type) {
        case SHOW_MORE_JUDGMENT_TWEETS:
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    tweetsShown: Math.min(state.frontend.tweetsShown + 10, state.backend.tweets.length),
                }
            }
        case RECEIVE_TWEETS_AND_JUDGMENTS:
            return {
                ...state,
                backend: {
                    ...state.backend,
                    ...action.tweetsAndJudgments,
                }
            }
        case FILTER_TWEETS: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    tweetFilter: action.judgment === state.frontend.tweetFilter ? 'all' : action.judgment,
                    tweetsShown: Math.min(30, state.backend.tweets.length),
                }
            }
        }
        default:
            return state
    }
}

const JudgmentButtons = ({judgment, onJudgmentClick}) => (
    <div className="tweet-outer-meta btn-group btn-block justify-content-center">
        <button className={`btn btn-${(judgment > 1) ? "" : "outline-"}success`} onClick={() => onJudgmentClick(2)}>Very</button>
        <button className={`btn btn-${(judgment > 0) ? "" : "outline-"}success`} onClick={() => onJudgmentClick(1)}>Relevant</button>
        <button className={`btn btn-${(judgment === null) ? "" : "outline-"}primary`}  onClick={() => onJudgmentClick(null)}>Unjudged</button>
        <button className={`btn btn-${(judgment == 0) ? "" : "outline-"}danger`}  onClick={() => onJudgmentClick(0)}>Irrelevant</button>
    </div>
)

const JudgedTweet = ({tweet, judgment, onJudgmentClick}) => (
    <div className="card tweet-outer">
        <TweetEmbed{...tweet} />
        <JudgmentButtons judgment={judgment} onJudgmentClick={judgment => onJudgmentClick(tweet.id, judgment)} />
    </div>
)

let TweetFilter = props => (
    <JudgmentButtons {...props} />
)

TweetFilter = connect(
    state => ({judgment: state.frontend.tweetFilter}),
    dispatch => ({
        onJudgmentClick: (judgment => {dispatch(filterTweets(judgment))})
    }),
)(TweetFilter)

import InfiniteScroll from 'redux-infinite-scroll';

let TweetJudgmentList = ({tweets, tweetsShown, showMore, judgments, onJudgmentClick, tweetFilter}) => {
    const filteredTweets = tweets.filter(tweet => (tweetFilter === 'all' || judgments[tweet.id] === tweetFilter))

    const doneMessage = <div className={"alert alert-success"} role="alert">
        <strong>All tweets are judged.</strong> <a className="alert-link" href={window.TOPICS_URL}>Show the topic list.</a>
    </div>

    if (!filteredTweets.length) {
        let message = ""
        let type = "warning"

        switch (tweetFilter) {
            case 2: {
                message = "There are no very relevant tweets."
                break
            }
            case 1: {
                message = "There are no relevant tweets."
                break
            }
            case 0: {
                message = "There are no irrelevant tweets."
                break
            }
            case null: {
                return doneMessage
            }
            default: {
                message = "There are no tweets."
                type = "danger"
            }
        }
        return <div className={`alert alert-${type}`} role="alert">
            <strong>{message}</strong>
        </div>

    }

    const done = !Object.values(judgments).filter((j) => (j === null)).length

    return <div>
        {done && doneMessage}
        <InfiniteScroll
               children={filteredTweets.slice(0, tweetsShown).map(tweet => (
                   <JudgedTweet
                       key={tweet.id}
                           tweet={tweet}
                           judgment={judgments[tweet.id]}
                           onJudgmentClick={onJudgmentClick}
                   />
               ))}
               loadMore={showMore}
               hasMore={filteredTweets.length > tweetsShown}
               elementIsScrollable={false}
        />
    </div>

}
TweetJudgmentList.propTypes = {
    tweets: PropTypes.array,
    tweetsShown: PropTypes.number,
    showMore: PropTypes.func,
    judgments: PropTypes.object,
    onJudgmentClick: PropTypes.func,
}
TweetJudgmentList = connect(
    state => ({
        tweets: state.backend.tweets,
        tweetsShown: state.frontend.tweetsShown,
        judgments: state.backend.judgments,
        tweetFilter: state.frontend.tweetFilter,
    }),
    dispatch => ({
        showMore: (
            () => {dispatch(showMoreJudgmentTweets())}
        ),
        onJudgmentClick: (
            (tweet_id, judgment) => {dispatch(judgeTweet(tweet_id, judgment))}
        ),
    })
)(TweetJudgmentList)

const JudgeApp = () => (
    <div className="row">
        <div className="col-6 bg-faded sidebar bd-links">
            <TopicInfo />
            <h2>Tweet filter</h2>
            <TweetFilter />
        </div>
        <main className="col offset-6">
            <TweetJudgmentList />
        </main>
    </div>
)

window.judge = () => {
    window.initialState = {
        backend: {
            ...window.BACKEND,
        },
        frontend: {
            tweetsShown: Math.min(30, window.BACKEND.tweets.length),
            tweetFilter: 'all',
        },
    }

    let store = createStore(
        tweetJudgeApp,
        window.initialState,
        applyMiddleware(thunkMiddleware, createLogger()),
    )
    window.store = store;

    render(
        <Provider store={store}>
            <JudgeApp />
        </Provider>,
        document.getElementById('main-content')
    )
}
