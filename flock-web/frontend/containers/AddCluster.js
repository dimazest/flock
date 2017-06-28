import React from 'react'
import { connect } from 'react-redux'

import { addCluster } from '../actions'


let AddCluster = ({ dispatch }) => {
    let input

    return (
        <div>
            <form
                className="sidebar-element"
                onSubmit={e => {
                        e.preventDefault()
                        if (!input.value.trim()) {
                            return
                        }
                        dispatch(addCluster(input.value))
                        input.value = ''
                }}
            >
                <div className="row" id="sidebar-search-box">
                    <div className="col-10">
                        <input
                            type="text"
                            className="form-control"
                            placeholder="New cluster gloss"
                            ref={node => {
                                    input = node
                            }}
                        />
                    </div>
                    <div className="col-2">
                        <button className="btn btn-outline-success my-2 my-sm-0 w-100" type="submit">Add</button>
                    </div>
                </div>
            </form>
        </div>
    )
}
AddCluster = connect()(AddCluster)

export default AddCluster
