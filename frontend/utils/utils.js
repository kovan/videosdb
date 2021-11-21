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
        if (process.env.DEBUG)
            db.useEmulator("127.0.0.1", 6001);
    } catch (e) {
        if (e.name != "FirebaseError")
            throw e
    }
    return db;
}

function formatDate(date) {

    console.log(typeof date)
    console.log(date)
    console.log(JSON.stringify(date))
    if (date instanceof Date)
        return date.toLocaleDateString()
    if (date instanceof String)
        return parseISO(date).toLocaleDateString()
    if (date instanceof firebase.firestore.Timestamp)
        return date.toDate().toLocaleDateString()
    if (date instanceof Object)
        return new Timestamp(date.seconds, date.nanoseconds).toDate().toLocaleDateString()
    throw TypeError
}

export { createDb, formatDate }

