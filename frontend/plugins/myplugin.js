import { getDb } from "~/utils/utils"
import { formatDate, dateToISO } from '~/utils/utils'


var db = null

export default function ({ app, $config, $db }, inject) {
    if (!$db) {
        db = getDb(app.$config.firebase)
    }

    inject("db", db)
    inject("myLog", console.log)
    inject("myDebugger", function () { debugger })
    inject("myFormatDate", formatDate)
    inject("myDateToISO", dateToISO)
}
