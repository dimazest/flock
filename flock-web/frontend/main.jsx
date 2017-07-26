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

/* Reducers*/

import { combineReducers } from 'redux'

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
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    activeClusterID: action.activeClusterID,
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

const loggerMiddleware = createLogger()

let store = createStore(
    tweetClusterApp,
    window.initialState,
    applyMiddleware(
        thunkMiddleware,
        loggerMiddleware,
    ),
)
window.store = store;

/* Presentational Components */

import { connect } from 'react-redux'
import PropTypes from 'prop-types'

let TopicInfo= ({ topic }) => {
    return <h1>Evaluation topic {topic.title}</h1>
}
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
                    <div className="col-10">
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
                    <div className="col-2">
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

const Cluster = ({ onActivateClick, onShowClick, gloss, size, active=false, visible=false }) => (
    <li
        className={"list-group-item " + (active ? "active " : "") + "justify-content-between"}
        onClick={onActivateClick}
    >
        <button className={"btn " + (visible ? "btn-info active " : "btn-outline-info")}
                onClick={
                    e => {
                        e.stopPropagation()
                        onShowClick()
                    }
                }
        >
            {visible ? "Show Unclustered" : `${size} tweets`}
        </button>
        <span className="ml-2">{gloss}</span>
    </li>
)
Cluster.propTypes = {
    onActivateClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired,
    gloss: PropTypes.string.isRequired,
    size: PropTypes.number.isRequired,
    active: PropTypes.bool,
    visible: PropTypes.bool
}

let ClusterList = ({ clusters, activeClusterID, activeTweetID, visibleClusterID, onActivateClick, onShowClick }) => (
    <div style={{overflowY: 'scroll', maxHeight: '90%'}}>
        <ul className="list-group">
            {
                clusters.map(
                    cluster => (
                        <Cluster key={cluster.id} gloss={cluster.gloss} size={cluster.size}
                                 onActivateClick={() => onActivateClick(activeTweetID, cluster.id)}
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
            onActivateClick: (activeTweetID, activeClusterID) => {dispatch(assignTweet(activeTweetID, activeClusterID))},
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

const TweetList = ({ tweets, onAssignClick, visibleClusterID=null, activeClusterID=null, activeTweetID=null }) => (
    <div>
    {tweetCluster(tweets, visibleClusterID).map(tweet => (
        <ClusteredTweet
            key={tweet.id}
            tweet={tweet}
            onAssignClick={() => onAssignClick(tweet.id, activeClusterID)}
            active={tweet.id === activeTweetID}
        />
    ))}
        </div>
)
TweetList.propTypes = {
    tweets: PropTypes.objectOf(PropTypes.array),
    onAssignClick: PropTypes.func.isRequired,
    visibleClusterID: PropTypes.number,
    activeClusterID: PropTypes.number,
    activeTweetID: PropTypes.string,
}

const TweetListContainer = connect(
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

const App = () => (
    <div className="row">
        <div className="col-6 bg-faded sidebar bd-links">
            <TopicInfo />
            <AddCluster />
            <ClusterList />
        </div>
        <main className="col-6 offset-6">
            <TweetListContainer />
        </main>
    </div>
)

render(
    <Provider store={store}>
        <App />
    </Provider>,
    document.getElementById('main-content')
);
