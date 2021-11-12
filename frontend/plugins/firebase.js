import { initializeApp } from 'firebase/app';
import { getFirestore } from 'firebase/firestore/lite'
import { getAuth, connectAuthEmulator } from "firebase/auth";




// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
    apiKey: "AIzaSyAL2IqFU-cDpNa7grJDxpVUSowonlWQFmU",
    authDomain: "worpdress-279321.firebaseapp.com",
    projectId: "worpdress-279321",
    storageBucket: "worpdress-279321.appspot.com",
    messagingSenderId: "149555456673",
    appId: "1:149555456673:web:5bb83ccdf79e8e47b3dee0",
    //measurementId: "G-CPNNB5CBJM"
};

// Initialize Firebase

var firebase = null;

export default function ({ app, $config }, inject) {
    if (!firebase) {
        firebase = initializeApp(firebaseConfig);
        const auth = getAuth(firebase);
        connectAuthEmulator(auth, "http://localhost:6001");


        const firestore = getFirestore(firebase)

        inject("firestore", firestore)
    }

}
