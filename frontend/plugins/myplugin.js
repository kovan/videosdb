import { getDb } from "~/utils/utils"


var db = null

export default function ({ app, $config, $db }, inject) {
    if (!$db) {
        db = getDb(app.$config.firebase)
    }

    inject("db", db)
    inject("mylog", console.log)
    inject("mydebugger", function () { debugger })
}
