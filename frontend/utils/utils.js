import firebase from 'firebase/app';
import { firestore } from 'firebase/firestore';


import { parseISO } from 'date-fns'

function createDb(config) {
    let db = null
    let app = null
    if (firebase.apps.length == 0) {
        app = firebase.initializeApp({
            apiKey: config.apiKey,
            authDomain: config.authDomain,
            projectId: config.projectId
        });
    } else {
        app = firebase.apps[0]

    }
    db = app.firestore();
    try {
        db.enablePersistence()
        db.settings({
            cacheSizeBytes: firebase.firestore.CACHE_SIZE_UNLIMITED,
            merge: true
        })
            .catch((err) => {
                if (err.code == 'failed-precondition') {
                    console.error("Multiple tabs open, persistence can only be enabled in one tab at a a time.")
                } else if (err.code == 'unimplemented') {
                    console.error("The current browser does not support all of the features required to enable persistence")
                }
            });
        if (process.env.DEBUG) {
            console.info("USING FIREBASE EMULATOR")
            db.useEmulator("127.0.0.1", 6001);
        }
    } catch (e) {
        if (e.name != "FirebaseError")
            throw e
    }
    return db;
}

function formatDate(date) {

    if (date instanceof Date)
        return date.toLocaleDateString()
    if (date instanceof String)
        return parseISO(date).toLocaleDateString()
    if (date instanceof firebase.firestore.Timestamp)
        return date.toDate().toLocaleDateString()
    if (date instanceof Object)
        return new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate().toLocaleDateString()

    throw TypeError()
}

async function getWithCache(query) {
    let snap = await query.get({ source: "cache" });
    if (snap.empty) {
        // cache didn't have anything, so try a fetch from server instead
        snap = await query.get();
    }
    return snap
}

export { createDb, formatDate }

