import 'babel-polyfill'

import React from 'react'
import { render } from 'react-dom'
import { Provider } from 'react-redux'
import { createStore, applyMiddleware } from 'redux'
import thunkMiddleware from 'redux-thunk'
import { createLogger } from 'redux-logger'
import InfiniteScroll from 'redux-infinite-scroll';

/* Helpers */

function tweetCluster(tweets, clusterID) {
    return tweets[clusterID] || []
}

function clusterNewName(tweets, clusterID){
    // const tw = tweetCluster(tweets, clusterID)

    // return tw.length > 0 ? tw[0].text : ''
    return ''
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
            window.CLUSTER_URL,
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
function activateCluster(activeClusterID, canDeselect=false){
    return {
        type: ACTIVATE_CLUSTER,
        activeClusterID,
        canDeselect,
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

const REQUEST_DELETE_CLUSTER = 'REQUEST_DELETE_CLUSTER'
function requestDeleteCluster(clusterID) {
    console.log(`Request delete cluster ${clusterID}`)

    return {
        type: REQUEST_DELETE_CLUSTER,
        clusterID,
    }
}

const CLUSTER_DELETED = 'CLUSTER_DELETED'
function clusterDeleted(clusterID) {
    return {
        type: CLUSTER_DELETED,
        clusterID,
    }
}

function deleteCluster(clusterID) {
    return dispatch => {
        dispatch(requestDeleteCluster(clusterID))

        return fetch(
            window.CLUSTER_URL,
            {
                credentials: 'include',
                method: 'DELETE',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({clusterID})
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured.', error)
            )
            .then(
                json => {
                    dispatch(receiveBackend(json))
                    dispatch(clusterDeleted(clusterID))
                }
            )
    }
}

const SHOW_MORE_TWEETS = 'SHOW_MORE_TWEETS'
function showMoreTweets(){
    return {type: SHOW_MORE_TWEETS}
}

const RECEIVE_TWEETS_AND_JUDGMENTS = 'RECEIVE_TWEETS_AND_JUDGMENTS'
function receiveTweetsAndJudgments(tweetsAndJudgments) {
    return {
        type: RECEIVE_TWEETS_AND_JUDGMENTS,
        tweetsAndJudgments,
    }
}

const FILTER_TWEETS = 'FILTER_TWEETS'
function filterTweets(judgment) {
    return {
        type: FILTER_TWEETS,
        judgment,
    }
}

const REQUEST_JUDGE_TWEET = 'REQUEST_JUDGE_TWEET'
function requestJudgeTweet(tweet_id, rts_id, topic_id, judgment){
    console.log(`Judge tweet ${tweet_id} ${rts_id} ${topic_id}: ${judgment}`)

    return {
        type: REQUEST_JUDGE_TWEET,
        tweet_id,
        rts_id,
        topic_id,
        judgment,
    }
}

function judgeTweet(tweet_id, rts_id, topic_id, judgment, selection_args, collection){
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
                body: JSON.stringify({
                    tweet_id,
                    rts_id,
                    collection,
                    topic_id,
                    judgment,
                    selection_args,
                }),
            },
        ).then(
            response => {

                if (window.TWEET_TASK_URL !== undefined) {
                    dispatch(receiveTask(window.TWEET_TASK_URL))
                }
                else if (window.STATE_URL !== undefined) {
                    dispatch(receiveState())
                } else {
                    dispatch(receiveBackend())
                }
            },
            error => console.log('An error occured', error)
        )
    }
}

const START_EDITING_CLUSTER = 'START_EDITING_CLUSTER'
function startEditingCluster(cluster) {
    return {
        ...cluster,
        type: START_EDITING_CLUSTER,
    }
}

const CANCEL_EDITING_CLUSTER = 'CANCEL_EDITING_CLUSTER'
function cancelEditingCluster() {
    return {type: CANCEL_EDITING_CLUSTER}
}

const CHANGE_EDITING_CLUSTER = 'CHANGE_EDITING_CLUSTER'
function changeEditingCluster(gloss) {
    return {
        type: CHANGE_EDITING_CLUSTER,
        gloss,
    }
}

const REQUEST_SUBMIT_EDITING_CLUSTER = 'REQUEST_SUBMIT_EDITIN_CLUSTER'
function requestSubmitEditingCluster(editingCluster) {
    console.log(`Request submit editing cluster ${editingCluster.id}, gloss:  ${editingCluster.gloss}`)
    return {
        ...editingCluster,
        type: REQUEST_SUBMIT_EDITING_CLUSTER,
    }
}

function submitEditingCluster(editingCluster) {
    return dispatch => {
        dispatch(requestSubmitEditingCluster(editingCluster))

        return fetch(
            window.CLUSTER_URL,
            {
                credentials: 'include',
                method: 'PUT',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({clusterID: editingCluster.id, gloss: editingCluster.gloss}),
            },
        )
            .then(
                response => response.json(),
                error => console.log('An error occured', error)
            )
            .then(
                json => {
                    dispatch(receiveBackend(json))
                    dispatch(cancelEditingCluster())
                }
            )
    }
}

const REQUEST_SWAP_CLUSTERS = 'REQUEST_SWAP_CLUSTERS'
function requestSwapClusters(clusterID1, clusterID2) {
    console.log(`Swap clusters ${clusterID1} and ${clusterID2}.`)
    return {
        type: REQUEST_SWAP_CLUSTERS,
        clusterID1,
        clusterID2,
    }
}


function swapClusters(clusterID1, clusterID2) {
    return dispatch => {

        if (clusterID1 === null || clusterID2 === null) {
            return
        }

        dispatch(requestSwapClusters(clusterID1, clusterID2))

        return fetch(
            window.SWAP_CLUSTERS_URL,
            {
                credentials: 'include',
                method: 'PUT',
                headers: {
                    'X-CSRFToken': window.CSRF_TOKEN,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({clusterID1, clusterID2}),
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

const REVERSE_TWEETS = 'REVERSE_TWEETS'
function reverseTweets() {
    return {
        type: REVERSE_TWEETS,
    }
}

const REQUEST_RECEIVE_TASK = 'REQUEST_RECEIVE_TASK'
function requestReceiveTask(url) {
    console.log(`Request task ${url}.`)
    return {
        type: REQUEST_RECEIVE_TASK,
        url,
    }
}

function receiveTask(url) {
    return dispatch => {
        dispatch(requestReceiveTask(url))

        return fetch(
            url,
            {credentials: 'include'},
        )
            .then(
                response => response.json(),
                error => console.log('An error occured', error)
            )
            .then(
                json => {
                    if (json.state === 'SUCCESS') {
                        dispatch(receiveTweetsAndJudgments(json.backendState))
                    } else if (json.state === 'PENDING') {
                        window.setTimeout(() => {dispatch(receiveTask(url))}, 1000)
                    } else {
                        console.log(`Could not get a task result.`)
                    }
                }
            )
    }
}

function receiveState() {
    return dispatch => {
        return fetch(
            window.STATE_URL,
            {credentials: 'include'},
        ).then(
            response => response.json(),
            error => console.log('Ann error occured', error),
        ).then(
            json => {
                if (window.CLUSTER_URL) {
                    dispatch(receiveBackend(json))
                } else {
                    dispatch(receiveTweetsAndJudgments(json))
                }
            }
        )
    }
}

/* Components */

import { connect } from 'react-redux'
import PropTypes from 'prop-types'

let TopicInfo= ({ topic, onUpdateClick, full=true}) => (
    <div>
        <div className="row">
            <h1 className="col">Evaluation topic {topic.title}</h1>
            <div className="col-2" style={{minWidth: "164px"}}
            >
                <button
                    type="button"
                    className="btn btn-outline-warning w-100 my-2 my-sm-0"
                    onClick={onUpdateClick}
                >Update</button>
            </div>
        </div>
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
                      <textarea className="form-control" type="text" value={topic.narrative} disabled={true} rows={7}/>
                  </div>
              </div>
             }
         </div>
        }
    </div>
)
TopicInfo = connect(
    state => ({topic: state.backend.topic}),
    dispatch => ({onUpdateClick: () => {
        dispatch(receiveState())
    }})
)(TopicInfo)

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
                        <button className="btn btn-success my-2 my-sm-0 w-100" type="submit">
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

const Cluster = ({ onActivateClick, onActivateAndAssignClick, onShowClick, onDeleteClick, onEditClick, id, gloss, size, active, visible,
                   editingCluster, onCancelClick, onClusterGlossChange, onSaveClusterClick, onMoveUpClick, onMoveDownClick }) => {

                       const editing = id === editingCluster.id

                       return (
                           <li className={"list-group-item " + (active ? "active " : "")}>
                               <div className="col col-1">
                                   <div className="btn-group-vertical">
                                       <button type="button" disabled={!onMoveUpClick} className="btn btn-secondary" onClick={onMoveUpClick}><i className="fa fa-arrow-up" aria-hidden="true"></i></button>
                                       <button type="button" disabled={!onMoveDownClick} className="btn btn-secondary" onClick={onMoveDownClick}><i className="fa fa-arrow-down" aria-hidden="true"></i></button>
                                   </div>
                               </div>
                               <div className="col">
                                   {!editing ?
                                    gloss :
                                    <div className="input-group">
                                        <textarea className="form-control" placeholder="Cluster gloss"
                                                  value={editingCluster.gloss}
                                                  onChange={ e => {e.preventDefault(); onClusterGlossChange(e.target.value)} }
                                                  rows="5"
                                        />
                                        <span className="input-group-btn">
                                            <button className="btn btn-success" type="button" onClick={e => {e.preventDefault(); onSaveClusterClick(editingCluster)}}>
                                                Save
                                            </button>
                                        </span>
                                        <span className="input-group-btn">
                                            <button className="btn btn-danger" type="button" onClick={e => {e.stopPropagation(); onCancelClick()}}>Cancel</button>
                                        </span>
                                    </div>
                                   }
                               </div>
                               <div className="btn-group col-9 col-lg-6 justify-content-end" style={{minWidth: "453px"}}>
                                   {!editing &&
                                    <button className={"btn btn-outline-warning" + (active ? " active" : "")} onClick={ e => {e.stopPropagation(); onEditClick()} }>Rename</button>
                                   }
                                   <button className={"btn btn-outline-danger" + (active ? " active" : "")} onClick={ e => {e.stopPropagation(); onDeleteClick()} }>Delete</button>
                                   <button className={"btn btn-outline-info" + (active || visible ? " active" : "")} onClick={ e => {e.stopPropagation(); onShowClick()} }>
                                       {visible ? "Show Unclustered" : `Show (${size})`}
                                   </button>
                                   <button className={"btn btn-secondary" + (active ? " active" : "")} onClick={e => {e.stopPropagation(); onActivateClick()}}>
                                       {active ? "Deselect" : "Select"}
                                   </button>
                                   <button className={"btn btn-primary" + (active ? " active" : "")} onClick={onActivateAndAssignClick}>Assign</button>
                               </div>
                           </li>
                       )
                   }
Cluster.propTypes = {
    onActivateClick: PropTypes.func.isRequired,
    onActivateAndAssignClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired,
    onDeleteClick: PropTypes.func.isRequired,
    onEditClick: PropTypes.func.isRequired,
    gloss: PropTypes.string.isRequired,
    size: PropTypes.number.isRequired,
    active: PropTypes.bool.isRequired,
    visible: PropTypes.bool.isRequired,
    editingCluster: PropTypes.shape(
        {
            id: PropTypes.number,
            gloss: PropTypes.string,
        }
    ).isRequired,
    onCancelClick: PropTypes.func.isRequired,
    onClusterGlossChange: PropTypes.func.isRequired,
    onSaveClusterClick: PropTypes.func.isRequired,
    onMoveUpClick: PropTypes.func,
    onMoveDownClick: PropTypes.func,
}

let ClusterList = (
    { clusters, activeClusterID, activeTweetID, visibleClusterID, onActivateClick, onActivateAndAssignClick, onShowClick, onDeleteClick, onEditClick, editingCluster, onCancelClick, onClusterGlossChange, onSaveClusterClick, swapClusters }
) => (
    <div style={{overflowY: 'scroll', maxHeight: '90%'}}>
        <ul className="list-group">
            {clusters.map((cluster, i) => (
                <Cluster key={cluster.id}
                         {...cluster}
                         onActivateClick={() => onActivateClick(cluster.id)}
                         onActivateAndAssignClick={() => onActivateAndAssignClick(activeTweetID, cluster.id)}
                         active={cluster.id === activeClusterID}
                         visible={cluster.id === visibleClusterID}
                         onShowClick={() => onShowClick(cluster.id)}
                         onDeleteClick={() => onDeleteClick(cluster.id)}
                         onEditClick={() => onEditClick(cluster)}
                         editingCluster={editingCluster}
                         onCancelClick={onCancelClick}
                         onClusterGlossChange={onClusterGlossChange}
                         onSaveClusterClick={onSaveClusterClick}
                         onMoveUpClick={clusters[i - 1] ? () => {swapClusters(cluster.id,  clusters[i - 1].id)} : null}
                         onMoveDownClick={clusters[i + 1] ? () => {swapClusters(cluster.id, clusters[i + 1].id)} : null}
                />
            ))}
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
    onShowClick: PropTypes.func.isRequired,
    onDeleteClick: PropTypes.func.isRequired,
    onEditClick: PropTypes.func.isRequired,
    editingCluster: PropTypes.shape(
        {
            id: PropTypes.number,
            gloss: PropTypes.string,
        }
    ).isRequired,
    onCancelClick: PropTypes.func.isRequired,
    onClusterGlossChange: PropTypes.func.isRequired,
    onSaveClusterClick: PropTypes.func.isRequired,
    swapClusters: PropTypes.func.isRequired,
}

ClusterList = connect(
    state => (
        {
            clusters: state.backend.clusters,
            activeClusterID: state.frontend.activeClusterID,
            activeTweetID: state.frontend.activeTweetID,
            visibleClusterID: state.frontend.visibleClusterID,
            editingCluster: state.frontend.editingCluster,
        }
    ),
    dispatch => (
        {
            onActivateClick: activeClusterID => {dispatch(activateCluster(activeClusterID, true))},
            onActivateAndAssignClick: (activeTweetID, activeClusterID) => {dispatch(assignTweet(activeTweetID, activeClusterID))},
            onShowClick: id => {dispatch(showCluster(id))},
            onDeleteClick: id => {dispatch(deleteCluster(id))},
            onEditClick: editingCluster => {dispatch(startEditingCluster(editingCluster))},
            onCancelClick: () => {dispatch(cancelEditingCluster())},
            onClusterGlossChange: gloss => {dispatch(changeEditingCluster(gloss))},
            onSaveClusterClick: editingCluster => {dispatch(submitEditingCluster(editingCluster))},
            swapClusters: (clusterID1, clusterID2) => {dispatch(swapClusters(clusterID1, clusterID2))},
        }
    )
)(ClusterList)

import TweetEmbed from './tweet-embed'
/* import TweetEmbed from 'react-tweet-embed'*/

const ClusteredTweet = ({ tweet, onAssignClick, active, onJudgmentClick }) => (
    <div className="row" key={tweet.id}>
        <div className="col-1" style={{margin: '10px'}}>
            <button className={"btn " +  (active ? "btn-primary " : "btn-outline-primary ")} style={{height: '100%'}} onClick={onAssignClick}>Assign</button>
        </div>
        <div className="col ml-1"  style={{maxWidth: '540px'}}>
            <TweetEmbed{...tweet} />
        </div>
        <div className="col-1" style={{margin: '10px'}}>
            <div className="btn-group-vertical" style={{height: "100%"}}>
                <button className="btn btn-outline-danger" style={{height: '50%'}} onClick={() => onJudgmentClick(0)}>
                    <i className="fa fa-thumbs-o-down" aria-hidden="true"></i>
                </button>
                <button className="btn btn-outline-warning" style={{height: '50%'}} onClick={() => onJudgmentClick('missing')}>
                    Missing
                </button>
            </div>
        </div>
    </div>
)
ClusteredTweet.propTypes = {
    tweet: PropTypes.object.isRequired,
    onAssignClick: PropTypes.func,
    active: PropTypes.bool,
    onJudgmentClick: PropTypes.func,
}

let TweetList = ({ tweets, onAssignClick, visibleClusterID=null, activeClusterID=null, activeTweetID=null, tweetsShown, showMore, onJudgmentClick, topic }) => {

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

    return <InfiniteScroll
        children={tweetsForCluster.slice(0, tweetsShown).map(tweet => (
            <ClusteredTweet
                key={tweet.id}
                tweet={tweet}
                onAssignClick={() => onAssignClick(tweet.id, activeClusterID)}
                active={tweet.id === activeTweetID}
                onJudgmentClick={judgment => onJudgmentClick(tweet.id, topic.rts_id, topic.topic_id, judgment, topic.collection)}
            />
        ))}
        loadMore={showMore}
        hasMore={tweetsForCluster.length > tweetsShown}
        elementIsScrollable={false}
    />

}
TweetList.propTypes = {
    topic: PropTypes.object.isRequired,
    tweets: PropTypes.objectOf(PropTypes.array),
    onAssignClick: PropTypes.func.isRequired,
    visibleClusterID: PropTypes.number,
    activeClusterID: PropTypes.number,
    activeTweetID: PropTypes.string,
    tweetsShown: PropTypes.number,
    showMore: PropTypes.func,
    onJudgmentClick: PropTypes.func,
}

TweetList = connect(
    state => (
        {
            topic: state.backend.topic,
            tweets: state.backend.tweets,
            visibleClusterID: state.frontend.visibleClusterID,
            activeClusterID: state.frontend.activeClusterID,
            activeTweetID: state.frontend.activeTweetID,
            tweetsShown: state.frontend.tweetsShown,
        }
    ),
    dispatch => (
        {
            onAssignClick: (tweet_id, activeClusterID) => {dispatch(assignTweet(tweet_id, activeClusterID))},
            showMore: (() => {dispatch(showMoreTweets())}),
            onJudgmentClick: (tweet_id, rts_id, topic_id, judgment, collection) => {dispatch(judgeTweet(tweet_id, rts_id, topic_id, judgment, null, collection))},
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
            const activeClusterID = (action.canDeselect && action.activeClusterID === state.frontend.activeClusterID) ? null : action.activeClusterID
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
                    tweetsShown: Math.min(30, tweetCluster(state.backend.tweets, visibleClusterID).length),
                    newClusterName: clusterNewName(state.backend.tweets, visibleClusterID),
                },
            }
        }
        case CHANGE_NEW_CLUSTER_NAME: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    newClusterName: action.newClusterName,
                },
            }
        }
        case CLUSTER_DELETED: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    activeClusterID: action.clusterID === state.frontend.activeClusterID ? null : state.frontend.activeClusterID,
                    visibleClusterID: action.clusterID == state.frontend.visibleClusterID ? null : state.frontend.visibleClusterID,
                    editingCluster: action.clusterID == state.frontend.editingCluster.id ? {id: null, gloss: null} : state.frontend.editingCluster,
                }
            }
        }
        case START_EDITING_CLUSTER: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    editingCluster: {
                        ...state.frontend.editingCluster,
                        id: action.id,
                        gloss: action.gloss,
                    }
                }
            }
        }
        case CANCEL_EDITING_CLUSTER: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    editingCluster: {
                        id: null,
                        gloss: null,
                    }
                },
            }
        }
        case CHANGE_EDITING_CLUSTER: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    editingCluster: {
                        ...state.frontend.editingCluster,
                        gloss: action.gloss,
                    }
                }
            }
        }
        case SHOW_MORE_TWEETS:
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    tweetsShown: Math.min(state.frontend.tweetsShown + 10, tweetCluster(state.backend.tweets, state.frontend.visibleClusterID).length),
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
            tweetsShown: Math.min(30, window.BACKEND.unassignedTweets.length),
            visibleClusterID: null,
            newClusterName: clusterNewName({null: window.BACKEND.unassignedTweets}, null),
            editingCluster: {id: null, gloss: null},
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
        case SHOW_MORE_TWEETS:
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
                    reverseTweets: false,
                }
            }
        }
        case REVERSE_TWEETS: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    reverseTweets: !state.frontend.reverseTweets,
                }
            }
        }
        default:
            return state
    }
}

const JudgmentButtons = ({judgment, onJudgmentClick, showMissingButton=true}) => {
    if (!judgment) {
        judgment = {
            assessor: null,
        }
    }
    return <div className="tweet-outer-meta btn-group btn-block justify-content-center">
        <button className={`btn btn-${(judgment.assessor > 1) ? "" : "outline-"}success`} onClick={() => onJudgmentClick(2)} title="Very relevant">
            <i className="fa fa-thumbs-up" aria-hidden="true"></i>
        </button>
        <button className={`btn btn-${(judgment.assessor > 0) ? "" : "outline-"}success`} onClick={() => onJudgmentClick(1)} title="Relevant">
            <i className="fa fa-thumbs-o-up" aria-hidden="true"></i>
        </button>
        {(judgment.crowd_relevant !== undefined || judgment.crowd_not_relevant !== undefined) &&
            <button className={`btn btn-${(judgment.crowd_relevant > 0) ? "" : "outline-"}success`} onClick={() => onJudgmentClick(1)} title="Crowd relevant">
                <sup>{judgment.crowd_relevant}</sup>⁄<sub>{judgment.crowd_relevant + judgment.crowd_not_relevant}</sub>
            </button>
        }
        <button className={`btn btn-${(judgment.assessor === null) ? "" : "outline-"}primary`}  onClick={() => onJudgmentClick(null)} title="Not judged">
            Not judged
        </button>
        {(judgment.crowd_relevant !== undefined || judgment.crowd_not_relevant !== undefined) &&
            <button className={`btn btn-${(judgment.crowd_not_relevant > 0) ? "" : "outline-"}danger`} onClick={() => onJudgmentClick(0)} title="Crowd not relevant">
                <sup>{judgment.crowd_not_relevant}</sup>⁄<sub>{judgment.crowd_relevant + judgment.crowd_not_relevant}</sub>
            </button>
        }
        <button className={`btn btn-${(judgment.assessor == 0) ? "" : "outline-"}danger`}  onClick={() => onJudgmentClick(0)} title="Not relevant">
            <i className="fa fa-thumbs-o-down" aria-hidden="true"></i>
        </button>
        {
          showMissingButton &&
          <button className={`btn btn-${(judgment.assessor == 'missing') ? "" : "outline-"}warning`}  onClick={() => onJudgmentClick('missing')} title="Missing">Missing</button>
        }
    </div>
}

const JudgedTweet = ({tweet, judgment, onJudgmentClick, showMissingButton=true, showJudgmentButton=true}) => (
    <div className="card tweet-outer">
        <TweetEmbed{...tweet} />
        {showJudgmentButton &&
            <JudgmentButtons judgment={judgment} onJudgmentClick={judgment => onJudgmentClick(tweet.id, judgment)} showMissingButton={showMissingButton} />
        }
    </div>
)

let TweetFilter = ({onReverseClick, reverseTweets, ...props}) => (
    <div className="row">
        <div className="col"><JudgmentButtons {...props} onReverseClick={() => console.log('Reverse')} /></div>
        <div className="col-3"><button className={`btn btn-secondary ${reverseTweets ? "active" : ""}`} onClick={onReverseClick}>Reverse</button></div>
    </div>
)

TweetFilter = connect(
    state => ({
        judgment: {assessor: state.frontend.tweetFilter},
        reverseTweets: state.frontend.reverseTweets,
    }),
    dispatch => ({
        onJudgmentClick: (judgment => {dispatch(filterTweets(judgment))}),
        onReverseClick: (() => {dispatch(reverseTweets())}),
    }),
)(TweetFilter)

let TweetJudgmentList = ({
  tweets, tweetsShown, showMore, judgments, selection_args, onJudgmentClick, tweetFilter,
  reverseTweets, topic, collection, tweetsRequested, showMissingButton=true
}) => {
    let filteredTweets = tweets.filter(tweet => (tweetFilter === 'all' || (judgments[tweet.id] || {assessor: null}).assessor === tweetFilter))

    if (reverseTweets) {
        filteredTweets = filteredTweets.reverse()
    }

    const doneMessage = <div className={"alert alert-success"} role="alert">
        <strong>All tweets are judged.</strong> <a className="alert-link" href={window.TOPICS_URL}>Show the topic list.</a>
    </div>

    let tweet_requested_message = null;
    if (tweetsRequested) {
        tweet_requested_message = <div className="alert alert-info">
            <strong>Loading tweets...</strong>
        </div>
    }

    if (!filteredTweets.length && !tweetsRequested) {
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

    const unjudgedTweets = tweets.filter(tweet => ((!judgments[tweet.id]) || judgments[tweet.id].assessor === null))
    const done = !unjudgedTweets.length

    return <div>
        {tweet_requested_message && !tweets.length && tweet_requested_message}
        {!tweet_requested_message && done && doneMessage}
        <InfiniteScroll
            children={filteredTweets.slice(0, tweetsShown).map(tweet => (
                <JudgedTweet
                    key={tweet.id}
                    tweet={tweet}
                    judgment={judgments[tweet.id]}
                    onJudgmentClick={(tweet_id, judgment) => onJudgmentClick(tweet_id, topic.rts_id, topic.topic_id, judgment, selection_args, collection)}
                    showMissingButton={showMissingButton}
                    showJudgmentButton={topic.topic_id || false}
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
    topic: PropTypes.object,
    collection: PropTypes.string,
    selection_args: PropTypes.object,
    onJudgmentClick: PropTypes.func,
    reverseTweets: PropTypes.bool.isRequired,
    tweetsRequested: PropTypes.bool,
}
TweetJudgmentList = connect(
    state => ({
        topic: state.backend.topic,
        tweets: state.backend.tweets,
        tweetsShown: state.frontend.tweetsShown,
        judgments: state.backend.judgments,
        tweetFilter: state.frontend.tweetFilter,
        reverseTweets: state.frontend.reverseTweets,
        selection_args: state.backend.selection_args,
        collection: state.backend.collection,
        tweetsRequested: state.frontend.tweetsRequested,
    }),
    dispatch => ({
        showMore: (() => {dispatch(showMoreTweets())}),
        onJudgmentClick: (
            (tweet_id, rts_id, topic_id, judgment, selection_args, collection) => {dispatch(judgeTweet(tweet_id, rts_id, topic_id, judgment, selection_args, collection))}
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
            reverseTweets: false,
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

function devJudgeApp(state={}, action) {
    switch (action.type) {
        case SHOW_MORE_TWEETS:
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
                },
                frontend: {
                    ...state.frontend,
                    tweetsRequested: false,
                },
            }
        case FILTER_TWEETS: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    tweetFilter: action.judgment === state.frontend.tweetFilter ? 'all' : action.judgment,
                    tweetsShown: Math.min(30, state.backend.tweets.length),
                    reverseTweets: false,
                }
            }
        }
        case REVERSE_TWEETS: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    reverseTweets: !state.frontend.reverseTweets,
                }
            }
        }
        case REQUEST_RECEIVE_TASK: {
            return {
                ...state,
                frontend: {
                    ...state.frontend,
                    tweetsRequested: true,
                }
            }
        }
        default:
            return state
    }
}

let DevJudgeApp = ({topic_id}) => (
    <div>
    {topic_id &&
      <div className="container mb-5">
        <div className="row">
          <div className="col-3"><h2>Tweet Filter</h2></div>
          <div className="col-9"><TweetFilter showMissingButton={false} /></div>
        </div>
      </div>
    }
      <TweetJudgmentList showMissingButton={false} />
    </div>
)
DevJudgeApp = connect(
    state => ({
        topic_id: state.backend.topic.topic_id
    })
)(DevJudgeApp)

window.devTweets = () => {
    window.initialState = {
        backend: {
            tweets: [],
            judgments: {},
            selection_args: window.SELECTION_ARGS,
            collection: window.COLLECTION,
            topic: {},
        },
        frontend: {
            tweetsShown: 0,
            tweetFilter: 'all',
            reverseTweets: false,
            tweetsRequested: false,
        },
    }

    let store = createStore(
        devJudgeApp,
        window.initialState,
        applyMiddleware(thunkMiddleware, createLogger()),
    )
    window.store = store;

    render(
        <Provider store={store}>
            <DevJudgeApp />
        </Provider>,
        document.getElementById('tweets')
    )

    store.dispatch(receiveTask(window.TWEET_TASK_URL))
}
