const functions = require("firebase-functions");

// // Create and Deploy Your First Cloud Functions
// // https://firebase.google.com/docs/functions/write-firebase-functions
//
// exports.helloWorld = functions.https.onRequest((request, response) => {
//   functions.logger.info("Hello logs!", {structuredData: true});
//   response.send("Hello from Firebase!");
// });


const admin = require("firebase-admin");
const express = require("express");
const { ApolloServer, gql } = require("apollo-server-express");
admin.initializeApp(functions.config().firebase);
// const serviceAccount = require('../serviceAccountKey.json');
// admin.initializeApp({
//   credential: admin.credential.cert(serviceAccount),
// });


const typeDefs = gql`
  type Jurado {
    nombre: String
    foto: String
    orden: Int
  }

  type Query {
    jurados: [Jurado]
    jurado(id: ID!): Jurado
  }
`;