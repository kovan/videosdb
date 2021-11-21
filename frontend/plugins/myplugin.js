import { createDb } from "~/utils/utils.server"



var db = null

export default function ({ app, $config }, inject) {
    if (!db) {
        db = createDb(app.$config.firebase)
    }

    inject("db", db)
}

