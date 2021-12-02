import firebase from 'firebase/app';

//import 'firebase/firestore/memory';
import { firestore } from 'firebase/firestore';
import { parseISO } from 'date-fns'
var db = null
var vuex_data = null

async function getVuexData(dbOptions) {
    if (!db)
        db = createDb(dbOptions)
    if (!vuex_data) {
        const query = db
            .collection('playlists')
            .orderBy('videosdb.lastUpdated', 'desc')

        const meta_query = db.collection('meta').doc('meta')

        let [results, meta_results] = await Promise.all([
            query.get(),
            meta_query.get(),
        ])
        let categories = []
        results.forEach((doc) => {
            let category = {
                name: doc.data().snippet.title,
                slug: doc.data().videosdb.slug,
                use_count: doc.data().videosdb.videoCount,
            }
            categories.push(category)
        })

        let meta_data = meta_results.data()
        vuex_data = {
            categories,
            meta_data
        }
    }
    return vuex_data
}

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
            db.useEmulator("127.0.0.1", 6001);

        }
    } catch (e) {
        if (e.name == "FirebaseError" && e.code == "failed-precondition")
            console.debug(e)
        else
            throw e
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
    return await query.get();
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

export { createDb, formatDate, getWithCache, getVuexData }

