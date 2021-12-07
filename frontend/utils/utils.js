import firebase from 'firebase/app';
//import 'firebase/firestore/memory';
import { firestore } from 'firebase/firestore';
import { formatISO, parseISO } from 'date-fns'

const FIREBASE_SETTINGS = {
    apiKey: "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU",
    authDomain: "worpdress-279321.firebaseapp.com",
    projectId: "worpdress-279321",
    storageBucket: "worpdress-279321.appspot.com",
    messagingSenderId: "149555456673",
    appId: "1:149555456673:web:5bb83ccdf79e8e47b3dee0",
    measurementId: "G-CPNNB5CBJM"
}


var db = null
var vuex_data = null

async function getVuexData(db) {
    if (vuex_data)
        return vuex_data

    console.log("getting vuex data")
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

    return vuex_data
}

function getDb(config) {
    if (db)
        return db

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

function dateToISO(date) {
    if (typeof date == "string")
        return date
    if (date instanceof Date)
        return formatISO(date)
    if (date instanceof firebase.firestore.Timestamp)
        return formatISO(date.toDate())
    if (date instanceof Object)
        return formatISO(new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate())

    throw TypeError()

}


async function dereferenceDb(id_list, collection) {
    let items = []
    const results =
        await collection
            .where('id', 'in', id_list)
            .get()

    results.forEach((doc) => {
        items.push(doc.data())
    })
    return items
}


export { getDb, formatDate, getVuexData, dereferenceDb, dateToISO, FIREBASE_SETTINGS }

