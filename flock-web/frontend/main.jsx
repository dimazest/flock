import 'babel-polyfill'

import React from 'react'
import { render } from 'react-dom'
import { Provider } from 'react-redux'
import { createStore } from 'redux'
import todoApp from './reducers'
import App from './components/App'

let store = createStore(
    todoApp,
    {
        visibilityFilter: 'SHOW_ALL',
        todos: [
            {
                text: 'Consider using Redux',
                completed: true,
                id: -1
            },
            {
                text: 'Keep all state in a single tree',
                completed: false,
                id: -2
            }
        ]
    }

)


render(
    <div>
        <div className="row">
            <div className="col-6 bg-faded sidebar bd-links">
                <Provider store={store}>
                    <App />
                </Provider>
            </div>
        </div>
        <main className="col-6 offset-6">
            Hello form React!
        </main>
    </div>,
    document.getElementById('main-content')
);
