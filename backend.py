import itertools
import os
from datetime import datetime, timezone, timedelta

import logging
import osuapi
import pymongo

logger = logging.getLogger(__name__)


def simplify(s):
    return s.strip().lower()


class Backend:
    def __init__(self, loop):
        logger.info('Initialising osuapi driver')
        self.api = osuapi.OsuApi(os.environ.get('osuapi'),
                                 connector=osuapi.AHConnector(loop=loop))
        logger.info('Initialising mongodb driver')
        client = pymongo.MongoClient(os.environ.get('MONGODB_URI'))
        self.db = client.get_database()

    def clean_db(self):
        for c in self.db.collection_names():
            self.db.drop_collection(c)

    def init_db(self):
        logger.info('Initialising db indices')
        self.db.subs.create_index([('attr', pymongo.ASCENDING), ('value', pymongo.ASCENDING)])
        self.db.links.create_index([('user', pymongo.ASCENDING), ('added', pymongo.ASCENDING)])
        self.db.links.create_index('sub')
        time = datetime.utcnow()
        logger.info(f'Setting last_check at {time}')
        self.db.last_check.insert_one({'time': time})

    def set_last_check(self, days_ago):
        time = datetime.now(tz=timezone(timedelta(hours=8))) - timedelta(days=days_ago)
        logger.info(f'Changing last_check to {time}')
        self.db.last_check.find_one_and_update({}, {'$set': {'time': time}})

    def add(self, user, attr, value):
        user_id = self.find_or_add('users', {'_id': user})
        sub_id = self.find_or_add('subs', {'attr': attr, 'value': value})
        self.find_or_add('links', {'user': user_id, 'sub': sub_id},
                         {'user': user_id, 'sub': sub_id, 'added': datetime.utcnow()})

    def find_or_add(self, collection, find, update=None):
        if update is None:
            update = find
        existing = self.db[collection].find_one_and_update(find, {'$setOnInsert': update}, upsert=True,
                                                           return_document=pymongo.ReturnDocument.AFTER)
        return existing['_id']

    def list(self, user):
        sub_ids = [doc['sub'] for doc in self.db.links.find({'user': user},
                                                            projection=['sub'],
                                                            sort=[('added', pymongo.ASCENDING)])]
        return sorted(self.db.subs.find({'_id': {'$in': sub_ids}}), key=lambda x: sub_ids.index(x['_id']))

    def remove(self, user, ix):
        doc = self.db.links.find_one({'user': user},
                                     projection=['sub'],
                                     sort=[('added', pymongo.ASCENDING)],
                                     skip=ix)
        self.db.links.delete_one({'_id': doc['_id']})
        sub = self.db.subs.find_one({'_id': doc['sub']})
        logger.info(f"Removed {user}'s subscription to {sub}")
        return sub

    def remove_all(self, user):
        logger.info(f'Removing {user} and all their subs')
        self.db.links.delete_many({'user': user})
        self.db.users.delete_one({'_id': user})

    async def check(self, notify_cb):
        time = datetime.utcnow()
        last_check = self.db.last_check.find_one_and_update({}, {'$set': {'time': time}})['time']
        logger.info(f'Changed last_check from {last_check} to {time}')
        last_check = last_check.astimezone(timezone(timedelta(hours=8)))
        logger.info(f'Querying osuapi with since={last_check}')
        beatmaps = await self.api.get_beatmaps(since=last_check)
        logger.info(f'Got {len(beatmaps)} new beatmaps')
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
