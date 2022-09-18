import { getDb, formatDate, dateToISO, getFirebaseSettings } from '~/utils/utils'


var db = null

export default defineNuxtPlugin(async (NuxtApp) => {
    //console.debug("executing plugin, db=", db, "$db=", context.$db)

    if (!db)
        db = getDb(await getFirebaseSettings(NuxtApp.payload.$config))


    return {
        provide: {
            $db: db,
            $myLog: console.log,
            $myDebugger: function () { debugger },
            $myFormatDate: formatDate,
            $myDateToISO: dateToISO
        }
    }
})
