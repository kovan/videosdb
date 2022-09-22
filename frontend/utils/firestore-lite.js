import { initializeApp, getApp } from "firebase/app";
import {
    getFirestore,
    connectFirestoreEmulator,
} from 'firebase/firestore/lite';


var db = null


function getDbLite(config) {
    if (db)
        return db

    let app = null
    try {
        app = getApp()
        db = getFirestore()
    } catch {
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
    getDbLite
}
