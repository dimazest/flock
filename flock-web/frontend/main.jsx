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

/* Actions */

const REQUEST_ADD_CLUSTER = 'REQUEST_ADD_CLUSTER'
function requestAddCluster(gloss){
    return {
        type: REQUEST_ADD_CLUSTER,
        gloss
    }
}

const RECEIVE_BACKEND = 'RECEIVE_BACKEND'
function receiveBackend(backend){
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
                body: JSON.stringify({
                    gloss: gloss,
                })
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured.', error)
            )
            .then(
                json => {
                    dispatch(
                        receiveBackend(
                            {
                                ...json,
                                tweets: {
                                    ...json.tweets,
                                    null: json.unassignedTweets,
                                },
                            },
                        )
                    )

                    dispatch(activateCluster(json.newClusterID))

                }
            )
    }
}

function assignTweet(tweet_id, cluster_id) {
    return dispatch => {
        console.log(`Assign tweet ${tweet_id} to cluster ${cluster_id}`)
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
            }
        case ACTIVATE_CLUSTER:
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    activeClusterID: action.activeClusterID,
                },
            }
        case SHOW_CLUSTER: {
            const visibleClusterID = action.visibleClusterID === state.frontend.visibleClusterID ? null : action.visibleClusterID
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    visibleClusterID: visibleClusterID,
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

let ClusterList = ({ clusters, activeClusterID, visibleClusterID, onActivateClick, onShowClick }) => (
    <div style={{overflowY: 'scroll', maxHeight: '90%'}}>
        <ul className="list-group">
            {
                clusters.map(
                    cluster => (
                        <Cluster key={cluster.id} gloss={cluster.gloss} size={cluster.size}
                                 onActivateClick={() => onActivateClick(cluster.id)}
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
    visibleClusterID: PropTypes.number,
    onActivateClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired
}

ClusterList = connect(
    state => (
        {
            clusters: state.backend.clusters,
            activeClusterID: state.frontend.activeClusterID,
            visibleClusterID: state.frontend.visibleClusterID,

        }
    ),
    dispatch => (
        {
            onActivateClick: id => {dispatch(activateCluster(id))},
            onShowClick: id => {dispatch(showCluster(id))},
        }
    )
)(ClusterList)

import TweetEmbed from './tweet-embed'
/* import TweetEmbed from 'react-tweet-embed'*/

const ClusteredTweet = ({ tweet, onAssignClick, disabled }) => (
    <div className="row" key={tweet.id}>
        <div className="col-1" style={{margin: '10px'}}>
            <button className="btn btn-primary" style={{height: '100%'}} onClick={onAssignClick} disabled={disabled}>Assign</button>
        </div>
        <div className="col ml-1">
            <TweetEmbed{...tweet} />
        </div>
    </div>
)
ClusteredTweet.propTypes = {
    tweet: PropTypes.object.isRequired,
    onAssignClick: PropTypes.func,
    disabled: PropTypes.bool,
}

const TweetList = ({ tweets, onAssignClick, visibleClusterID=null, activeClusterID=null }) => (
    <div>
        {tweetCluster(tweets, visibleClusterID).map(tweet => (
            <ClusteredTweet
                key={tweet.id}
                tweet={tweet}
                onAssignClick={() => onAssignClick(tweet.id, activeClusterID)}
                disabled={activeClusterID === null}
            />
        ))}
    </div>
)
TweetList.propTypes = {
    tweets: PropTypes.objectOf(PropTypes.array),
    onAssignClick: PropTypes.func.isRequired,
    visibleClusterID: PropTypes.number,
    activeClusterID: PropTypes.number,
}

const TweetListContainer = connect(
    state => (
        {
            tweets: state.backend.tweets,
            visibleClusterID: state.frontend.visibleClusterID,
            activeClusterID: state.frontend.activeClusterID,
        }
    ),
    dispatch => (
        {
            onAssignClick: (tweetID, activeClusterID) => {dispatch(assignTweet(tweetID, activeClusterID))}
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
