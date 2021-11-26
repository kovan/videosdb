import { initializeApp } from 'firebase/app'

import { getDocs, getFirestore, connectFirestoreEmulator } from 'firebase/firestore/lite'

// //import 'firebase/firestore/memory';
// import { firestore } from 'firebase/firestore';
import { parseISO } from 'date-fns'

function createDb(config) {
    let db = null
    let app = null

    //if (firebase.apps.length == 0) {
    app = initializeApp({
        apiKey: config.apiKey,
        authDomain: config.authDomain,
        projectId: config.projectId
    });
    // } else {
    //     app = firebase.apps[0]

    // }
    db = getFirestore(app);

    // try {
    // db.enablePersistence()
    // db.settings({
    //     cacheSizeBytes: firebase.firestore.CACHE_SIZE_UNLIMITED,
    //     synchronizeTabs: true,
    //     merge: true
    // })
    //     .catch((err) => {
    //         if (err.code == 'failed-precondition') {
    //             console.error("Multiple tabs open, persistence can only be enabled in one tab at a a time.")
    //         } else if (err.code == 'unimplemented') {
    //             console.error("The current browser does not support all of the features required to enable persistence")
    //         }
    //     });

    try {
        if (process.env.NODE_ENV === 'development') {
            console.info("USING FIREBASE EMULATOR")
            connectFirestoreEmulator(db, "127.0.0.1", 6001)

        }
    } catch (e) {
        if (e.name != "FirebaseError")
            throw e
        else
            console.debug(e)
    }
    return db;
}

function formatDate(date) {

    if (typeof date == "string")
        return parseISO(date).toLocaleDateString()
    if (date instanceof Date)
        return date.toLocaleDateString()
    if (date instanceof firebase.firestore.Timestamp)
        return date.toDate().toLocaleDateString()
    if (date instanceof Object)
        return new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate().toLocaleDateString()

    throw TypeError()
}

async function getWithCache(query) {
    return await getDocs(query)
    // let snap = null
    // try {
    //     snap = await query.get({ source: "cache" });
    // } catch (e) {
    //     // not in cache
    //     if (e.code != "unavailable")
    //         throw e
    // }
    // if (!snap || snap.empty) {
    //     // cache didn't have anything, so try a fetch from server instead
    //     snap = await query.get();
    // }
    // return snap
}

export { createDb, formatDate, getWithCache }

