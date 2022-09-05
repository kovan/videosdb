import { google, GoogleApis } from 'googleapis'
import { initializeApp } from 'firebase/app'
import { getFirestore, collection, getDoc, doc } from 'firebase/firestore/lite'
import { main, createQueue, spawn, all } from 'effection';
import { firebase_sadhguru } from './firebase-settings.js'
import "path"



class DB {
    constructor() {

        let project = process.env["VIDEOSDB_FIREBASE_PROJECT"]
        let config = process.env["VIDEOSDB_CONFIG"]
        console.info("Current project: " + project)
        this.firestoreApp = initializeApp(firebase_sadhguru)
        this.db = getFirestore(this.firestoreApp);
    }
    async init() {
        const metaDoc = doc(this.db, "meta/meta")
        let snapshot = await getDoc(metaDoc)
    }
    async getETag(collection, id) {
        docRef = doc(this.db, collection, id)
        docSnp = await getDoc(docRef)
        return docSnp.exists ? docSnp.etag : null
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
    * check_for_new_videos() {
        console.info("Sync start")
        /*         yield this.db.init() */

        /*         logger.info("Currently there are %s videos in the DB",
                    await self.db.get_video_count()) */
        let videoQueue = createQueue("Video queue")
        let playlistQueue = createQueue("Playlist queue")

        yield spawn(this._playlistRetriever(playlistQueue))
        yield spawn(this._playlistProcessor(playlistQueue, videoQueue))
        yield spawn(this._videoProcessor(videoQueue))
        console.info("Sync finished")

    }

    async _playlistRetriever(playlistQueue) {
        let params = {
            "part": "snippet,contentDetails,statistics",
            "id": this.YT_CHANNEL_ID
        }
        console.info("Retrieving channel " + this.YT_CHANNEL_ID)
        let channel_info = await this.api.channels.list(params)
        console.log(channel_info)
    }
    async _playlistProcessor(playlistQueue, videoQueue) {
    }
    async _videoProcessor(videoQueue) {
    }
}



main(function* () {
    let d = new Downloader()

    yield spawn(d.check_for_new_videos())
})
