import { getDb, formatDate, dateToISO } from '~/utils/utils'


var db = null

export default function ({ app }, inject) { // real args are: context and inject
    if (!db)
        db = getDb(app.$config.firebase)

    inject("db", db)
    inject("myLog", console.log)
    inject("myDebugger", function () { debugger })
    inject("myFormatDate", formatDate)
    inject("myDateToISO", dateToISO)
}
