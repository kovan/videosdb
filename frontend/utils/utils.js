
import { formatISO, parseISO } from 'date-fns'
import {
    query, collection, orderBy, getDoc, getDocs, doc, Timestamp
} from 'firebase/firestore';




/**
 * Removes invalid XML characters from a string
 * @param {string} str - a string containing potentially invalid XML characters (non-UTF8 characters, STX, EOX etc)
 * @param {boolean} removeDiscouragedChars - should it remove discouraged but valid XML characters
 * @return {string} a sanitized string stripped of invalid XML characters
 */
function removeXMLInvalidChars(string, removeDiscouragedChars = true) {
    // remove everything forbidden by XML 1.0 specifications, plus the unicode replacement character U+FFFD
    var regex = /((?:[\0-\x08\x0B\f\x0E-\x1F\uFFFD\uFFFE\uFFFF]|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?:[^\uD800-\uDBFF]|^)[\uDC00-\uDFFF]))/g;
    string = string.replace(regex, "");

    if (removeDiscouragedChars) {
        // remove everything not suggested by XML 1.0 specifications
        regex = new RegExp(
            "([\\x7F-\\x84]|[\\x86-\\x9F]|[\\uFDD0-\\uFDEF]|(?:\\uD83F[\\uDFFE\\uDFFF])|(?:\\uD87F[\\uDF" +
            "FE\\uDFFF])|(?:\\uD8BF[\\uDFFE\\uDFFF])|(?:\\uD8FF[\\uDFFE\\uDFFF])|(?:\\uD93F[\\uDFFE\\uD" +
            "FFF])|(?:\\uD97F[\\uDFFE\\uDFFF])|(?:\\uD9BF[\\uDFFE\\uDFFF])|(?:\\uD9FF[\\uDFFE\\uDFFF])" +
            "|(?:\\uDA3F[\\uDFFE\\uDFFF])|(?:\\uDA7F[\\uDFFE\\uDFFF])|(?:\\uDABF[\\uDFFE\\uDFFF])|(?:\\" +
            "uDAFF[\\uDFFE\\uDFFF])|(?:\\uDB3F[\\uDFFE\\uDFFF])|(?:\\uDB7F[\\uDFFE\\uDFFF])|(?:\\uDBBF" +
            "[\\uDFFE\\uDFFF])|(?:\\uDBFF[\\uDFFE\\uDFFF])(?:[\\0-\\t\\x0B\\f\\x0E-\\u2027\\u202A-\\uD7FF\\" +
            "uE000-\\uFFFF]|[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]|[\\uD800-\\uDBFF](?![\\uDC00-\\uDFFF])|" +
            "(?:[^\\uD800-\\uDBFF]|^)[\\uDC00-\\uDFFF]))", "g");
        string = string.replace(regex, "");
    }

    return string;
}





var vuex_data = null

async function getVuexData(db) {
    if (vuex_data)
        return vuex_data


    console.log("getting vuex data")
    const q = query(collection(db, "playlists"), orderBy('videosdb.lastUpdated', 'desc'))
    const meta_query = doc(db, "meta/meta")

    let [results, meta_results] = await Promise.all([
        getDocs(q),
        getDoc(meta_query),
    ])
    let categories = []
    results.forEach((doc) => {
        let category = {
            name: doc.data().snippet.title,
            slug: doc.data().videosdb.slug,
            use_count: doc.data().videosdb.videoCount,
            last_updated: doc.data().videosdb.lastUpdated != null ? doc.data().videosdb.lastUpdated.toDate() : null
        }
        categories.push(category)
    })
    categories.sort()

    let meta_data = meta_results.data()
    vuex_data = {
        categories,
        meta_data
    }

    return vuex_data
}



function formatDate(date) {

    let result = null

    if (date instanceof Timestamp) {
        result = date.toDate()
    } else if (typeof date == "object" || date instanceof Object) {
        result = new Timestamp(date.seconds, date.nanoseconds).toDate()
    } else if (typeof date == "string" || date instanceof String) {
        result = parseISO(date)
    }

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return result.toLocaleDateString(undefined, options)


}

function dateToISO(date) {
    if (typeof date == "string")
        return date
    if (date instanceof Date)
        return formatISO(date)
    if (date instanceof Timestamp)
        return formatISO(date.toDate())
    if (date instanceof Object)
        return formatISO(new Timestamp(date.seconds, date.nanoseconds).toDate())

    throw TypeError()

}


async function dereferenceDb(db, id_list, collection) {
    let items = []

    for (let _id of id_list) {
        let doc_ref = doc(db, `${collection}/${_id}`)
        let doc_snapshot = await getDoc(doc_ref)
        if (doc_snapshot.exists) {
            items.push(doc_snapshot.data())
        }

    }
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
                description: //video.snippet.description
                    //? removeXMLInvalidChars(video.snippet.description, true).substring(0, 2040)
                    video.snippet.title,
                duration: video.videosdb.durationSeconds,
                publication_date: dateToISO(video.snippet.publishedAt)
            },
        ],
        priority: 1.0,
    }

    // if ('filename' in video.videosdb) {
    //     json.video[0].content_loc =
    //         'https://videos.sadhguru.digital/' +
    //         encodeURIComponent(video.videosdb.filename)
    // } else {
    //     json.video[0].player_loc = `https://www.youtube.com/watch?v=${video.id}`

    // }


    return json
}

function videoToStructuredData(video) {
    // Reference:
    // https://developers.google.com/search/docs/advanced/sitemaps/video-sitemaps
    let json = {
        '@context': 'https://schema.org',
        '@type': 'VideoObject',
        name: video.snippet.title,
        description: video.snippet.description
            ? video.snippet.description
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

    formatDate,
    getVuexData,
    dereferenceDb,
    dateToISO,
    videoToStructuredData,
    videoToSitemapEntry,
}

