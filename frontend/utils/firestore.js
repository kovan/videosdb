import { initializeApp, getApp } from "firebase/app";
import {
    getFirestore,
    connectFirestoreEmulator,
} from 'firebase/firestore';


var db = null


function getDb(config) {
    if (db)
        return db

    let app = null
    try {
        app = getApp()
        db = getFirestore()
    } catch (e) {
        console.log(e)
        app = initializeApp(config)
        db = getFirestore()
        console.debug(process.env)
        if (process.env.FIRESTORE_EMULATOR_HOST != undefined) {
            console.info("Using FIREBASE EMULATOR")
            connectFirestoreEmulator(db, ...process.env.FIRESTORE_EMULATOR_HOST.split(":"));
        } else {
            console.info("Using LIVE database.")
        }
    }

    return db;
}

export {
    getDb
}
