import React from 'react'
import Footer from './Footer'
import AddCluster from '../containers/AddCluster'
import VisibleTodoList from '../containers/VisibleTodoList'

const App = () => (
  <div>
    <AddCluster />
    <VisibleTodoList />
    <Footer />
  </div>
)

export default App
