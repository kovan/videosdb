import firebase from 'firebase/app';
import firestore from 'firebase/firestore';


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

export { createDb }

