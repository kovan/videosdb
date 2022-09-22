import { formatDate } from '~/utils/utils'
import { getFirebaseSettings } from "~/utils/firestore-common"
import { getDbLite } from "~/utils/firestore-lite"
var db = null

export default async function (context, inject) { // real args are: context and inject
    //console.debug("executing plugin, db=", db, "$db=", context.$db)
    if (!db)
        db = getDbLite(await getFirebaseSettings(context.$config))

    inject("db", db)
    inject("myFormatDate", formatDate)

}
