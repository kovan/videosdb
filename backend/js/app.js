import { google } from 'googleapis'
import { initializeApp } from 'firebase/app';
import { getFirestore, collection, getDoc, doc } from 'firebase/firestore/lite';
import "path"


const firebase_sadhguru = {
    apiKey: "AIzaSyAhKg1pGeJnL_ZyD1wv7ZPXwfZ6_7OBRa8",
    authDomain: "videosdb-firebase.firebaseapp.com",
    projectId: "videosdb-firebase",
    storageBucket: "videosdb-firebase.appspot.com",
    messagingSenderId: "136865344383",
    appId: "1:136865344383:web:2d9764597f98be41c7884a"
}


class DB {
    constructor() {

        let project = process.env["VIDEOSDB_FIREBASE_PROJECT"]
        let config = process.env["VIDEOSDB_CONFIG"]
        console.info("Current project: " + project)
        this.firestoreApp = initializeApp(firebase_sadhguru)
        this.db = getFirestore(this.firestoreApp);
    }
    async init() {
        const mydoc = doc(this.db, "meta/meta")
        let snapshot = await getDoc(mydoc)
    }
}

class Downloader {
    constructor(exclude_transcripts = false) {
        this.YT_CHANNEL_ID = process.env.YOUTUBE_CHANNEL_ID
        this.valid_video_ids = []
        this.db = new DB()
        this.api = google.youtube({
            version: 'v3',
            auth: process.env.YOUTUBE_API_KEY
        })
    }
    async init() {
        await this.db.init()
    }
    async check_for_new_videos() {
        console.info("Sync start")
        await this.init()

        console.info("Sync finished")
    }
}

let d = new Downloader()
await d.check_for_new_videos()
