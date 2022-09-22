import { formatDate } from '~/utils/utils'
import { getFirebaseSettings } from "~/utils/firestore-common"
import { getDb } from "~/utils/firestore"


var db = null

export default async function (context, inject) { // real args are: context and inject
    //console.debug("executing plugin, db=", db, "$db=", context.$db)
    if (!db)
        db = getDb(await getFirebaseSettings(context.$config))

    inject("db", db)
    inject("myFormatDate", formatDate)

}
