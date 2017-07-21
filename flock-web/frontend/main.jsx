import 'babel-polyfill'

import React from 'react'
import { render } from 'react-dom'
import { Provider } from 'react-redux'
import { createStore } from 'redux'

/* Action types */

const ADD_CLUSTER = 'ADD_CLUSTER'
const ACTIVATE_CLUSTER = 'ACTIVATE_CLUSTER'
const SHOW_CLUSTER = 'SHOW_CLUSTER'

/* Action creators*/

function addCluster(gloss){
    return {
        type: ADD_CLUSTER,
        gloss
    }
}

function activateCluster(activeClusterID){
    return {
        type: ACTIVATE_CLUSTER,
        activeClusterID,
    }
}

function showCluster(visibleClusterID){
    return {
        type: SHOW_CLUSTER,
        visibleClusterID,
    }
}

/* Reducers*/

import { combineReducers } from 'redux'

const initialState = {
    clusters: {
        clusters: [
            {id: -1, gloss: "Cluster A"},
            {id: -2, gloss: "Cluster B"},
            {id: -3, gloss: "Cluster C"}
        ],
        activeClusterID: -1,
        visibleClusterID: null
    },
    tweets: {
        [-1]: [
            {id: '888434623822393344', text: 'Gene Kelly on the streets of London, 1955'},
            {id: '-1A', text: 'Deleted: -1A'},
            {id: '-1B', text: 'Deleted -1B'}
        ],
        [-2]: [
            {id: '-2A', text: 'Deleted: -2A'},
            {id: '888463839746019328', text: "It's EXACTLY one month until peak #eclipse2017 in the DC area! Where will you be at 2:21pm on 8/21?"},
            {id: '-2B', text: 'Deleted -2B'}
        ],
        [-3]: [
            {id: '-3A', text: 'Deleted: -3A'},
            {id: '888068879595048965', text: "Main kit laid out for @TheLondonTri bike checked and ready to go. Just need to sort my @ScienceinSport #fuelling now."},
            {id: '-3B', text: 'Deleted -3B'}
        ],
        null: [
            {id: '21', text: 'just setting up my twttr'},
            {id: '761974145169195008', text: 'The Flight Club Weekender Presents Brunch Social #londonrestaurant #londonbars #londonfood'},
            {id: '760409556530896896', text: 'Rail disruption in the East #Midlands: how you can still reach #London by train ...http://www.itv.com/news/central/2016-08-02/rail-disruption-in-the-east-midlands-all-you-need-to-know/ …'},
            {id: '760772202136469504', text: 'Sous Chef Rosette Restaurant #London #AArosette Apply Here http://chefjob.co/CSM3810AA  Please Share / RT'}
        ]
    }
}

function clusters(state={}, action) {
    switch (action.type) {
        case ADD_CLUSTER:
            return {
                ...state,
                clusters: [...state.clusters, {gloss: action.gloss, id: state.clusters.length}],
                activeClusterID: state.clusters.length
            }
        case ACTIVATE_CLUSTER:
            return {
                ...state,
                activeClusterID: action.activeClusterID,
            }
        case SHOW_CLUSTER:
            return {
                ...state,
                visibleClusterID: action.visibleClusterID === state.visibleClusterID ? null : action.visibleClusterID
            }
        default:
            return state
    }
}

function tweets(state={}, action){
    return state
}

/* Main reducer */

const tweetClusterApp = combineReducers({clusters, tweets})

let store = createStore(
    tweetClusterApp,
    /* window.STATE_FROM_SERVER*/
    initialState,
)
window.store = store;

/* Presentational Components */

import { connect } from 'react-redux'
import PropTypes from 'prop-types'

let AddCluster = ({ dispatch }) => {
    let input

    return (
        <div className="mb-4">
            <form
                onSubmit={
                    e => {
                        e.preventDefault()
                        if (!input.value.trim()) {
                            return
                        }
                        dispatch(addCluster(input.value))
                        input.value = ''
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
AddCluster = connect()(AddCluster)

const Cluster = ({ onActivateClick, onShowClick, gloss, active=false, visible=false }) => (
    <li
        className={"list-group-item " + (active ? "active " : "")}
        onClick={onActivateClick}
    >
        <a className={"btn " + (visible ? "btn-warning active" : "btn-secondary")} href="#" role="button"
           onClick={
               e => {
                   e.stopPropagation()
                   onShowClick()
               }
           }
        >
            {visible ? "Show Unclustered" : "Show"}
        </a>
        <span className="ml-2">{gloss}</span>
    </li>
)
Cluster.propTypes = {
    onActivateClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired,
    gloss: PropTypes.string.isRequired,
    active: PropTypes.bool,
    visible: PropTypes.bool
}

const ClusterList = ({ clusters, onActivateClick, onShowClick }) => (
    <ul className="list-group">
        {
            clusters.clusters.map(
                cluster => (
                    <Cluster key={cluster.id} gloss={cluster.gloss}
                             onActivateClick={() => onActivateClick(cluster.id)}
                             active={cluster.id === clusters.activeClusterID}
                             onShowClick={() => onShowClick(cluster.id)}
                             visible={cluster.id === clusters.visibleClusterID}
                    />
                )
            )
        }
    </ul>
)
ClusterList.propTypes = {
    clusters: PropTypes.shape(
        {
            clusters: PropTypes.arrayOf(
                PropTypes.shape(
                    {
                        id: PropTypes.number.isRequired,
                        gloss: PropTypes.string.isRequired
                    }
                ).isRequired
            ).isRequired,
            activeClusterID: PropTypes.number.isRequired,
            shownClusterID: PropTypes.number,
        }
    ),
    onActivateClick: PropTypes.func.isRequired,
    onShowClick: PropTypes.func.isRequired
}

const ClusterListContainer = connect(
    state => ({clusters: state.clusters}),
    dispatch => (
        {
            onActivateClick: id => {dispatch(activateCluster(id))},
            onShowClick: id => {dispatch(showCluster(id))},
        }
    )
)(ClusterList)

/* import TweetEmbed from './tweet-embed'*/
import TweetEmbed from 'react-tweet-embed'

const TweetList = ({ tweets, visibleClusterID=null }) => (
    <div>{(
            tweets[visibleClusterID] || []).map(
                tweet => (
                    <TweetEmbed
                        key={tweet.id} id={tweet.id}
                    />
                )
            )}
    </div>
)
TweetList.propTypes = {
    tweets: PropTypes.objectOf(PropTypes.array),
    visibleClusterID: PropTypes.number
}

const TweetListContainer = connect(state => ({tweets: state.tweets, visibleClusterID: state.clusters.visibleClusterID}))(TweetList)

const App = () => (
    <div className="row">
        <div className="col-6 bg-faded sidebar bd-links">
            <AddCluster />
            <ClusterListContainer />
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
