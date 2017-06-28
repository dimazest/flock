let nextClusterId = 0
export const addCluster = text => {
  return {
    type: 'ADD_CLUSTER',
    id: nextClusterId++,
    text
  }
}

export const setVisibilityFilter = filter => {
  return {
    type: 'SET_VISIBILITY_FILTER',
    filter
  }
}

export const toggleTodo = id => {
  return {
    type: 'TOGGLE_TODO',
    id
  }
}

