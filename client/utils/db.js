import knex from 'knex';


class DB {
    constructor() {
        this.db = knex({
            client: 'pg',
            version: '7.2',
            connection: {
                host: '127.0.0.1',
                user: 'myuser',
                password: 'mypass',
                database: 'videosdb'
            }
        });
    }
    async getVideos() {
        let result = await this.db.select().from('videosdb_video').where({ excluded: false }).limit(10);
        return result;
    }

    async getVideo(slug) {
        let result = await this.db.select().from('videosdb_video').where({ slug: slug });
        if (result.length > 0)
            return result[0]
        return null
    }

}
let db = new DB()

export default db