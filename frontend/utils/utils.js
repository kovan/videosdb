import firebase from 'firebase/app';
//import 'firebase/firestore/memory';
import { firestore } from 'firebase/firestore';
import { formatISO, parseISO } from 'date-fns'
import logger from '@nuxtjs/sitemap/lib/logger';

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


/**
 * Removes invalid XML characters from a string
 * @param {string} str - a string containing potentially invalid XML characters (non-UTF8 characters, STX, EOX etc)
 * @param {boolean} removeDiscouragedChars - should it remove discouraged but valid XML characters
 * @return {string} a sanitized string stripped of invalid XML characters
 */
function removeXMLInvalidChars(str, removeDiscouragedChars) {

    // remove everything forbidden by XML 1.0 specifications, plus the unicode replacement character U+FFFD
    var regex = /((?:[\0-\x08\x0B\f\x0E-\x1F\uFFFD\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]))/g;

    // ensure we have a string
    str = String(str || '').replace(regex, '');

    if (removeDiscouragedChars) {

        // remove everything discouraged by XML 1.0 specifications
        regex = new RegExp(
            '([\\x7F-\\x84]|[\\x86-\\x9F]|[\\uFDD0-\\uFDEF]|(?:\\uD83F[\\uDFFE\\uDFFF])|(?:\\uD87F[\\uDF' +
            'FE\\uDFFF])|(?:\\uD8BF[\\uDFFE\\uDFFF])|(?:\\uD8FF[\\uDFFE\\uDFFF])|(?:\\uD93F[\\uDFFE\\uD' +
            'FFF])|(?:\\uD97F[\\uDFFE\\uDFFF])|(?:\\uD9BF[\\uDFFE\\uDFFF])|(?:\\uD9FF[\\uDFFE\\uDFFF])' +
            '|(?:\\uDA3F[\\uDFFE\\uDFFF])|(?:\\uDA7F[\\uDFFE\\uDFFF])|(?:\\uDABF[\\uDFFE\\uDFFF])|(?:\\' +
            'uDAFF[\\uDFFE\\uDFFF])|(?:\\uDB3F[\\uDFFE\\uDFFF])|(?:\\uDB7F[\\uDFFE\\uDFFF])|(?:\\uDBBF' +
            '[\\uDFFE\\uDFFF])|(?:\\uDBFF[\\uDFFE\\uDFFF])(?:[\\0-\\t\\x0B\\f\\x0E-\\u2027\\u202A-\\uD7FF\\' +
            'uE000-\\uFFFF]|[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]|[\\uD800-\\uDBFF](?![\\uDC00-\\uDFFF])|' +
            '(?:[^\\uD800-\\uDBFF]|^)[\\uDC00-\\uDFFF]))', 'g');

        str = str.replace(regex, '');
    }

    return str;
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
    }
    return settings
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
            last_updated: doc.data().videosdb.lastUpdated != null ? doc.data().videosdb.lastUpdated.toDate() : null
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
        console.debug(process.env)
        if (process.env.FIRESTORE_EMULATOR_HOST != undefined) {
            console.info("Using FIREBASE EMULATOR")
            db.useEmulator(...process.env.FIRESTORE_EMULATOR_HOST.split(":"));
        } else {
            console.info("Using LIVE database.")
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

    let result = null
    //console.log("DATE IS " + JSON.stringify(date))
    if (date instanceof firebase.firestore.Timestamp) {
        result = date.toDate()
    } else if (typeof date == "object" || date instanceof Object) {
        result = new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate()
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
    if (date instanceof firebase.firestore.Timestamp)
        return formatISO(date.toDate())
    if (date instanceof Object)
        return formatISO(new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate())

    throw TypeError()

}


async function dereferenceDb(id_list, collection) {
    let items = []
    id_list.forEach(async (id) => {
        let doc_ref = collection.doc(id)
        let doc = await doc_ref.get()
        if (doc.exists)
            items.push(doc.data())
    })
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
                description: video.snippet.description
                    ? removeXMLInvalidChars(video.snippet.description, false).substring(0, 2048)
                    : video.snippet.title,
                duration: video.videosdb.durationSeconds,
                publication_date: dateToISO(video.snippet.publishedAt)
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
    // Reference:
    // https://developers.google.com/search/docs/advanced/sitemaps/video-sitemaps
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
    }

    if ('filename' in video.videosdb) {
        json.contentUrl =
            'https://videos.sadhguru.digital/' +
            encodeURIComponent(video.videosdb.filename)

    } else {
        json.embedUrl = `https://www.youtube.com/watch?v=${video.id}`

    }



    let string = JSON.stringify(json)
    return string
}


export {
    getDb,
    formatDate,
    getVuexData,
    dereferenceDb,
    dateToISO,
    videoToStructuredData,
    videoToSitemapEntry,
    getFirebaseSettings
}

