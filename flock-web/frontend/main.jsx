import 'babel-polyfill'

import React from 'react'
import { render } from 'react-dom'
import { Provider } from 'react-redux'
import { createStore } from 'redux'

/* import todoApp from './reducers'*/
/* import App from './components/App'*/

/* let store = createStore(
 *     todoApp,
 *     {
 *         visibilityFilter: 'SHOW_ALL',
 *         todos: [
 *             {
 *                 text: 'Consider using Redux',
 *                 completed: true,
 *                 id: -1
 *             },
 *             {
 *                 text: 'Keep all state in a single tree',
 *                 completed: false,
 *                 id: -2
 *             }
 *         ]
 *     }
 * 
 * )
 * */

/* render(
 *     <div>
 *         <div className="row">
 *             <div className="col-6 bg-faded sidebar bd-links">
 *                 <Provider store={store}>
 *                     <App />
 *                 </Provider>
 *             </div>
 *         </div>
 *         <main className="col-6 offset-6">
 *             Hello form React!
 *         </main>
 *     </div>,
 *     document.getElementById('main-content')
 * );*/


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
        activeClusterID: -2,
        visibleClusterID: null
    },
    tweets: {
        [-1]: ['-1_A', '-1_B', '-1_C'],
        [-2]: ['-2_A', '-2_B', '-2_C', '-2_D'],
        [-3]: ['-3_A', '-3_B'],
        null: ['A', 'B', 'C', 'D']
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

const Tweet = ({ tweet_id }) => (
    <li>
        {tweet_id}
    </li>
)
Tweet.propTypes = {
    tweet_id: PropTypes.string.isRequired
}

const TweetList = ({ tweets, visibleClusterID=null }) => (
    <ul>
        {
            (tweets[visibleClusterID] || []).map(
                tweet => (
                    <Tweet key={tweet} tweet_id={tweet} />
                )
            )
        }
    </ul>
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
