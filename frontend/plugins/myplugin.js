import { getDb, formatDate, dateToISO, getFirebaseSettings } from '~/utils/utils'




var db = null

export default async function (context, inject) { // real args are: context and inject
    //console.debug("executing plugin, db=", db, "$db=", context.$db)
    if (!db)
        db = getDb(await getFirebaseSettings(context.$config))

    inject("db", db)
    inject("myLog", console.log)
    inject("myDebugger", function () { debugger })
    inject("myFormatDate", formatDate)
    inject("myDateToISO", dateToISO)
}
