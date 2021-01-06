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
    async getPublications() {
        let result = await this.db.select().from('videosdb_video').limit(10);
        return result;
    }

}
let db = new DB()

export default db