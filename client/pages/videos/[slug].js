import Head from 'next/head'
import Link from 'next/link'
import styles from '../../styles/Home.module.css'
import db from '../../utils/db.js'


export default function Video(data) {
  debugger
  return (
    <div>
      <Head>
        <title>Create Next App</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <h1> HELLO
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