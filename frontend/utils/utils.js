import { initializeApp } from 'firebase/app'

import { getDocs, getFirestore, connectFirestoreEmulator, Timestamp } from 'firebase/firestore/lite'

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
        if (!("DONT_USE_EMULATOR" in process.env)) {
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
    if (date instanceof Timestamp)
        return date.toDate().toLocaleDateString()
    if (date instanceof Object)
        return new Timestamp(date.seconds, date.nanoseconds).toDate().toLocaleDateString()

    throw TypeError()
}

export { createDb, formatDate }

