import itertools
from configparser import ConfigParser
from datetime import datetime, timezone, timedelta
from pprint import pprint

import osuapi
import pymongo

config = ConfigParser()
config.read('config.ini')


def simplify(s):
    return s.strip().lower()


class Backend:
    def __init__(self, loop):
        self.api = osuapi.OsuApi(config['osuapi']['key'],
                                 connector=osuapi.AHConnector(loop=loop))
        client = pymongo.MongoClient('mongodb://localhost:27017/')
        self.db = client.data
        self.init_db()

    def init_db(self):
        for c in self.db.collection_names():
            self.db.drop_collection(c)
        self.db.subs.create_index([('attr', pymongo.HASHED)])
        self.db.subs.create_index([('value', pymongo.HASHED)])
        self.db.links.create_index([('user', pymongo.HASHED)])
        self.db.links.create_index([('sub', pymongo.HASHED)])
        self.db.links.create_index([('added', pymongo.ASCENDING)])
        self.db.last_check.insert_one({'time': datetime.now(tz=timezone(timedelta(hours=8))) - timedelta(days=4)})

    def add(self, user, attr, value):
        user_id = self.find_or_add('users', {'_id': user})
        sub_id = self.find_or_add('subs', {'attr': attr, 'value': value})
        link_id = self.find_or_add('links', {'user': user_id, 'sub': sub_id,
                                             'added': datetime.utcnow()})

    def find_or_add(self, collection, doc):
        existing = self.db[collection].find_one(doc)
        if existing is None:
            return self.db[collection].insert_one(doc).inserted_id
        else:
            return existing['_id']

    def list(self, user):
        sub_ids = [doc['sub'] for doc in self.db.links.find({'user': user},
                                                            projection=['sub']).sort('added')]
        return self.db.subs.find({'_id': {'$in': sub_ids}})

    def remove(self, user, ix):
        sub_id = self.db.links.find_one_and_delete({'user': user},
                                                   projection=['sub'],
                                                   sort=[('added', pymongo.ASCENDING)],
                                                   skip=ix)['sub']
        sub = self.db.subs.find_one({'_id': sub_id})
        return sub

    def remove_all(self, user):
        self.db.links.delete_many({'user': user})
        self.db.users.delete_one({'_id': user})

    async def check(self, notify_cb):
        last_check = self.db.last_check.find_one_and_update({},
                                                            {'$set': {'time': datetime.now(
                                                                tz=timezone(timedelta(hours=8)))}})['time']
        print(last_check)
        beatmaps = await self.api.get_beatmaps(since=last_check)
        pprint([b.artist for b in beatmaps])
        groups = itertools.groupby(beatmaps, lambda r: r.beatmapset_id)
        to_notify = []
        to_notify_append = to_notify.append
        attrs = self.db.subs.distinct('attr')
        for _, group in groups:
            group = list(group)
            beatmap = group[0]
            notified = set()
            for attr in attrs:
                subs = self.db.subs.find({'attr': attr,
                                          'value': simplify(getattr(beatmap, attr))})
                for sub in subs:
                    user_ids = (doc['user'] for doc in
                                self.db.links.find({'sub': sub['_id']},
                                                   projection=['user']))
                    for user in user_ids:
                        if user not in notified:
                            to_notify_append((user, group, sub))
                            notified.add(user)
        for i in to_notify:
            await notify_cb(*i)
