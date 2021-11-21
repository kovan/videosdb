import firebase from 'firebase/app';
import firestore from 'firebase/firestore';

function createDb(config) {
    let db = null;
    try {
        db = firebase.firestore()
    } catch (e) {
        if (e.name == "FirebaseError") {
            const firebaseApp = firebase.initializeApp({
                apiKey: config.apiKey,
                authDomain: config.authDomain,
                projectId: config.projectId
            });
            db = firebase.firestore()
        } else
            throw e
    }
    if (process.env.DEBUG) {
        db.useEmulator("127.0.0.1", 6001);
    }
    return db;
}


var db = null

export default function ({ app, $config }, inject) {
    if (!db) {
        db = createDb(app.$config.firebase)
    }

    inject("db", db)
}

