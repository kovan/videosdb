function createDb(config) {
    const firebaseApp = firebase.initializeApp({
        apiKey: config.apiKey,
        authDomain: authDomain,
        projectId: projectId
    });

    return firebase.firestore();
}

export { createDb }

