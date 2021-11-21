const firebase = require("firebase");
// Required for side-effects
require("firebase/firestore");

// function createDb(config) {
//     if (!firebase.app()) {
//         const firebaseApp = firebase.initializeApp({
//             apiKey: config.apiKey,
//             authDomain: config.authDomain,
//             projectId: config.projectId
//         });
//     }
//     let db = firebase.firestore()
//     if (process.env.DEBUG) {
//         db.useEmulator("127.0.0.1", 6001);
//     }
//     return db;
// }


var db = null

export default function ({ app, $config }, inject) {
    if (!db) {
        db = firebase.firestore()
    }

    inject("db", db)
}

