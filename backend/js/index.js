import { google } from 'googleapis'
google.youtube({
    version: 'v3',
    auth: process.env.YOUTUBE_API_KEY
})


