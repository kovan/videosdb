// import firebase from 'firebase/compat/app';
// //import 'firebase/firestore/memory';
// import { firestore } from 'firebase/compat/firestore';
import { formatISO, parseISO } from 'date-fns'

// import { initializeApp } from "firebase/compat/app";

import { initializeApp, getApp } from "firebase/app";
import {
    getFirestore,
    getDoc,
    getDocs,
    orderBy,
    doc,
    connectFirestoreEmulator,
    query, collection,
    Timestamp
} from 'firebase/firestore';

const firebase_sadhguru = {
    apiKey: "AIzaSyAhKg1pGeJnL_ZyD1wv7ZPXwfZ6_7OBRa8",
    authDomain: "videosdb-firebase.firebaseapp.com",
    projectId: "videosdb-firebase",
    storageBucket: "videosdb-firebase.appspot.com",
    messagingSenderId: "136865344383",
    appId: "1:136865344383:web:2d9764597f98be41c7884a"
}


const firebase_nithyananda = {
    apiKey: "AIzaSyAokazNFM0aCatQ2HLQI2EmsL_fJvTUWyQ",
    authDomain: "videosdb-nithyananda.firebaseapp.com",
    projectId: "videosdb-nithyananda",
    storageBucket: "videosdb-nithyananda.appspot.com",
    messagingSenderId: "550038984532",
    appId: "1:550038984532:web:c69ab834dc3da08481dac1",
    measurementId: "G-9FCP7M1VDV"
};

const firebase_testing = {
    apiKey: "AIzaSyB4ssPNsGaIpFv8GNiBl-MbRWzRbuYV-MM",
    authDomain: "videosdb-testing.firebaseapp.com",
    projectId: "videosdb-testing",
    storageBucket: "videosdb-testing.appspot.com",
    messagingSenderId: "224322811272",
    appId: "1:224322811272:web:82113e7ad6fa250915763d"
};


/**
 * Removes invalid XML characters from a string
 * @param {string} str - a string containing potentially invalid XML characters (non-UTF8 characters, STX, EOX etc)
 * @param {boolean} removeDiscouragedChars - should it remove discouraged but valid XML characters
 * @return {string} a sanitized string stripped of invalid XML characters
 */
function removeXMLInvalidChars(string, removeDiscouragedChars = true) {
    // remove everything forbidden by XML 1.0 specifications, plus the unicode replacement character U+FFFD
    var regex = /((?:[\0-\x08\x0B\f\x0E-\x1F\uFFFD\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]))/g;
    string = string.replace(regex, "");

    if (removeDiscouragedChars) {
        // remove everything not suggested by XML 1.0 specifications
        regex = new RegExp(
            "([\\x7F-\\x84]|[\\x86-\\x9F]|[\\uFDD0-\\uFDEF]|(?:\\uD83F[\\uDFFE\\uDFFF])|(?:\\uD87F[\\uDF" +
            "FE\\uDFFF])|(?:\\uD8BF[\\uDFFE\\uDFFF])|(?:\\uD8FF[\\uDFFE\\uDFFF])|(?:\\uD93F[\\uDFFE\\uD" +
            "FFF])|(?:\\uD97F[\\uDFFE\\uDFFF])|(?:\\uD9BF[\\uDFFE\\uDFFF])|(?:\\uD9FF[\\uDFFE\\uDFFF])" +
            "|(?:\\uDA3F[\\uDFFE\\uDFFF])|(?:\\uDA7F[\\uDFFE\\uDFFF])|(?:\\uDABF[\\uDFFE\\uDFFF])|(?:\\" +
            "uDAFF[\\uDFFE\\uDFFF])|(?:\\uDB3F[\\uDFFE\\uDFFF])|(?:\\uDB7F[\\uDFFE\\uDFFF])|(?:\\uDBBF" +
            "[\\uDFFE\\uDFFF])|(?:\\uDBFF[\\uDFFE\\uDFFF])(?:[\\0-\\t\\x0B\\f\\x0E-\\u2027\\u202A-\\uD7FF\\" +
            "uE000-\\uFFFF]|[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]|[\\uD800-\\uDBFF](?![\\uDC00-\\uDFFF])|" +
            "(?:[^\\uD800-\\uDBFF]|^)[\\uDC00-\\uDFFF]))", "g");
        string = string.replace(regex, "");
    }

    return string;
}


async function getFirebaseSettings(config) {


    let current_config = config ? config.config : process.env.VIDEOSDB_CONFIG
    let settings = null
    switch (current_config) {
        case "nithyananda":
            settings = firebase_nithyananda
            break
        case "sadhguru":
            settings = firebase_sadhguru
            break
        case "testing":
            settings = firebase_testing
            break
    }
    return settings
}





var vuex_data = null

async function getVuexData(db) {
    if (vuex_data)
        return vuex_data

    console.log("getting vuex data")
    const q = query(collection(db, "playlists"), orderBy('videosdb.lastUpdated', 'desc'))

    let [results] = await Promise.all([
        getDocs(q)
    ])
    let categories = []
    results.forEach((doc) => {
        let category = {
            name: doc.data().snippet.title,
            slug: doc.data().videosdb.slug,
            use_count: doc.data().videosdb.videoCount,
            last_updated: doc.data().videosdb.lastUpdated != null ? doc.data().videosdb.lastUpdated.toDate() : null
        }
        categories.push(category)
    })
    categories.sort()

    vuex_data = {
        categories
    }

    return vuex_data
}

var db = null


function getDb(config) {
    if (db)
        return db

    let app = null
    try {
        app = getApp()
        db = getFirestore()
    } catch {
        app = initializeApp(config)
        db = getFirestore()
        console.log(process.env)
        if (process.env.FIRESTORE_EMULATOR_HOST != undefined) {
            console.info("Using FIREBASE EMULATOR")
            connectFirestoreEmulator(db, ...process.env.FIRESTORE_EMULATOR_HOST.split(":"));
        } else {
            console.info("Using LIVE database.")
        }
    }

    return db;
}

function formatDate(date) {

    let result = null

    if (date instanceof Timestamp) {
        result = date.toDate()
    } else if (typeof date == "object" || date instanceof Object) {
        result = new Timestamp(date.seconds, date.nanoseconds).toDate()
    } else if (typeof date == "string" || date instanceof String) {
        result = parseISO(date)
    }

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return result.toLocaleDateString(undefined, options)


}

function dateToISO(date) {
    if (typeof date == "string")
        return date
    if (date instanceof Date)
        return formatISO(date)
    if (date instanceof Timestamp)
        return formatISO(date.toDate())
    if (date instanceof Object)
        return formatISO(new Timestamp(date.seconds, date.nanoseconds).toDate())

    throw TypeError()

}


async function dereferenceDb(db, id_list, collection) {
    let items = []

    for (let _id of id_list) {
        let doc_ref = doc(db, `${collection}/${_id}`)
        let doc_snapshot = await getDoc(doc_ref)
        if (doc_snapshot.exists()) {
            items.push(doc_snapshot.data())
        }

    }
    return items
}


function videoToSitemapEntry(video) {
    // Reference:
    // https://developers.google.com/search/docs/advanced/sitemaps/video-sitemaps
    let json = {
        url: `/video/${video.videosdb.slug}`,
        video: [
            {
                thumbnail_loc: video.snippet.thumbnails.medium.url,
                title: video.snippet.title,
                description: //video.snippet.description
                    //? removeXMLInvalidChars(video.snippet.description, true).substring(0, 2040)
                    video.snippet.title,
                duration: video.videosdb.durationSeconds,
                publication_date: dateToISO(video.snippet.publishedAt),
                player_loc: `https://www.youtube.com/watch?v=${video.id}`
            },
        ],
        priority: 1.0,
    }

    // if ('filename' in video.videosdb) {
    //     json.video[0].content_loc =
    //         'https://videos.sadhguru.digital/' +
    //         encodeURIComponent(video.videosdb.filename)
    // } else {
    //     json.video[0].player_loc = `https://www.youtube.com/watch?v=${video.id}`

    // }


    return json
}

function videoToStructuredData(video) {

    let json = {
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        name: video.snippet.title,
        description: video.snippet.description
            ? video.snippet.description
            : video.snippet.title,
        thumbnailUrl: Object.values(video.snippet.thumbnails).map(
            (thumb) => thumb.url
        ),
        uploadDate: dateToISO(video.snippet.publishedAt),
        duration: video.contentDetails.duration,
        embedUrl: `https://www.youtube.com/watch?v=${video.id}`
    }

    // if ('filename' in video.videosdb) {
    //     json.contentUrl =
    //         'https://videos.sadhguru.digital/' +
    //         encodeURIComponent(video.videosdb.filename)

    // } else {
    //     json.embedUrl = `https://www.youtube.com/watch?v=${video.id}`

    // }



    let string = JSON.stringify(json)
    return string
}

function installUnhandledExceptionHandlers() {
    process.on('unhandledRejection', (error) => {
        console.trace(error);
    });

    process.on('uncaughtException', (error) => {
        console.error(error)
    })

}

export {
    getDb,
    formatDate,
    getVuexData,
    dereferenceDb,
    dateToISO,
    videoToStructuredData,
    videoToSitemapEntry,
    getFirebaseSettings,
    installUnhandledExceptionHandlers
}

