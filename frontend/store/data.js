export const state = () => ({
    categories: [],
    meta_doc: {}
})

export const mutations = {
    add(state, obj) {
        state.categories.push({
            obj,
            done: false
        })
    },
    // remove(state, { todo }) {
    //     state.list.splice(state.list.indexOf(todo), 1)
    // },
    // toggle(state, todo) {
    //     todo.done = !todo.done
    // }
}