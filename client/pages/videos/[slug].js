import Head from 'next/head'
import Link from 'next/link'
import db from '../../utils/db.js'


export default function Video(data) {
  return (
    <div>
      <Head>
        <title>Create Next App</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <p>
        Title:
      </p>
      <h1>
        {data.data.title}
      </h1>


    </div>)
}


export async function getServerSideProps(context) {

  var video = await db.getVideo(context.query.slug)
  console.log(video)
  return {
    props: {
      data: video
    }, // will be passed to the page component as props
  }
}