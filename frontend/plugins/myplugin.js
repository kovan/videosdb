import { getDb, formatDate, dateToISO, FIREBASE_SETTINGS } from '~/utils/utils'


var db = null

export default function ({ app }, inject) { // real args are: context and inject
    if (!db)
        db = getDb(FIREBASE_SETTINGS)

    inject("db", db)
    inject("myLog", console.log)
    inject("myDebugger", function () { debugger })
    inject("myFormatDate", formatDate)
    inject("myDateToISO", dateToISO)
}
