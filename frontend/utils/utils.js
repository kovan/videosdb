import firebase from 'firebase/app';
//import 'firebase/firestore/memory';
import { firestore } from 'firebase/firestore';
import { formatISO, parseISO } from 'date-fns'

const FIREBASE_SETTINGS = {
    apiKey: "AIzaSyAhKg1pGeJnL_ZyD1wv7ZPXwfZ6_7OBRa8",
    authDomain: "videosdb-firebase.firebaseapp.com",
    projectId: "videosdb-firebase",
    storageBucket: "videosdb-firebase.appspot.com",
    messagingSenderId: "136865344383",
    appId: "1:136865344383:web:2d9764597f98be41c7884a"
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
            last_updated: doc.data().videosdb.lastUpdated.toDate()
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
        date = parseISO(date)
    else if (date instanceof firebase.firestore.Timestamp)
        date = date.toDate()
    else if (date instanceof Object)
        date = new firebase.firestore.Timestamp(date.seconds, date.nanoseconds).toDate()
    if (!(date instanceof Date))
        throw TypeError()

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString(undefined, options)


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

    await Promise.all(id_list.map(async (id) => {
        let doc = await collection.doc("id").get()
        items.push(doc.data())
    }));

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
                description: video.videosdb.descriptionTrimmed
                    ? video.videosdb.descriptionTrimmed
                    : video.snippet.title,
                duration: video.videosdb.durationSeconds,
                publication_date: dateToISO(video.snippet.publishedAt)
            },
        ],
        priority: 1.0,
    }

    if ('filename' in video.videosdb) {
        json.video[0].content_loc =
            'https://videos.sadhguru.digital/' +
            encodeURIComponent(video.videosdb.filename)
    } else {
        json.video[0].player_loc = `https://www.youtube.com/watch?v=${video.id}`

    }


    return json
}

function videoToStructuredData(video) {
    // Reference:
    // https://developers.google.com/search/docs/advanced/sitemaps/video-sitemaps
    let json = {
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        name: video.snippet.title,
        description: video.videosdb.descriptionTrimmed
            ? video.videosdb.descriptionTrimmed
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
    FIREBASE_SETTINGS
}

