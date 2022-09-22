
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




export {
    getFirebaseSettings
}
