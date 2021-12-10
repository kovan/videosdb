import { getDb, formatDate, dateToISO, FIREBASE_SETTINGS } from '~/utils/utils'


var db = null

export default function (context, inject) { // real args are: context and inject
    //console.debug("executing plugin, db=", db, "$db=", context.$db)
    if (!db)
        db = getDb(FIREBASE_SETTINGS)

    inject("db", db)
    inject("myLog", console.log)
    inject("myDebugger", function () { debugger })
    inject("myFormatDate", formatDate)
    inject("myDateToISO", dateToISO)
}
