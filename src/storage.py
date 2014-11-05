#!/usr/bin/env python
# coding: utf-8

#########################################################################
#########################################################################

"""
   File Name: storage.py
      Author: Wan Ji
      E-mail: wanji@live.com
  Created on: Tue Nov  4 11:25:03 2014 CST
"""
DESCRIPTION = """
"""

import itertools
from struct import pack, unpack
import lmdb
import cPickle as pickle


class LMDBAccessor(object):
    def __init__(self, env, dbname):
        self.env = env
        self.db = env.open_db(dbname)

    def close(self):
        return
        self.db.close()

    def setkv(self, key, val, ktype, vtype):
        with self.env.begin(write=True) as txt:
            txt.cursor(self.db).put(pack(ktype, key), pack(vtype, key))

    def setk(self, key, val, ktype):
        with self.env.begin(write=True) as txt:
            txt.cursor(self.db).put(pack(ktype, key), val)

    def setv(self, key, val, vtype):
        with self.env.begin(write=True) as txt:
            txt.cursor(self.db).put(key, pack(vtype, val))

    def set(self, key, val):
        with self.env.begin(write=True) as txt:
            txt.cursor(self.db).put(key, val)

    def getkv(self, key, ktype, vtype):
        with self.env.begin(write=True) as txt:
            val = txt.cursor(self.db).get(pack(ktype, key))
            if val is None:
                return None
            return unpack(vtype, val)[0]

    def getk(self, key, ktype):
        with self.env.begin(write=True) as txt:
            return txt.cursor(self.db).get(pack(ktype, key))

    def getv(self, key, vtype):
        with self.env.begin(write=True) as txt:
            val = txt.cursor(self.db).get(key)
            if val is None:
                return None
            return unpack(vtype, val)[0]

    def get(self, key):
        with self.env.begin(write=True) as txt:
            return txt.cursor(self.db).get(key)

    def setkivi(self, key, val):
        self.setkv(key, val, 'i', 'i')

    def setki(self, key, val):
        self.setk(key, val, 'i')

    def setvi(self, key, val):
        self.setv(key, val, 'i')

    def getkivi(self, key):
        return self.getkv(key, 'i', 'i')

    def getki(self, key):
        return self.getk(key, 'i')

    def getvi(self, key):
        return self.getv(key, 'i')


class PQStorage(object):
    def __init__(self, pardic=None):
        self.blocks = None
        self.keys = None
        self.num_emptys = -1
        self.num_items = -1

    def get_num_items(self):
        return self.num_items

    def get_num_emptys(self):
        return self.num_emptys

    def __iter__(self):
        raise Exception("Instance of `PQStorage` is not allowed!")

    def next(self):
        raise Exception("Instance of `PQStorage` is not allowed!")

    def clear(self):
        raise Exception("Instance of `PQStorage` is not allowed!")


class MemPQStorage(PQStorage):
    def __init__(self, pardic=None):
        PQStorage.__init__(self)
        self.blocks = []
        self.keys = []
        self.num_items = 0

    def add(self, codes, keys):
        self.blocks.append(codes)
        self.keys.append(keys)
        self.num_items += codes.shape[0]

    def __iter__(self):
        return itertools.izip(self.keys, self.blocks)


class LMDBPQStorage(PQStorage):
    def __init__(self, pardic=None):
        PQStorage.__init__(self)

        path = pardic['path']
        clear = pardic.get('clear', False)

        self.env = lmdb.open(path, map_size=2**30, max_dbs=3)
        self.db_keys = LMDBAccessor(self.env, 'keys')
        self.db_vals = LMDBAccessor(self.env, 'vals')
        self.db_info = LMDBAccessor(self.env, 'info')

        if clear:
            self.clear()

        self.num_items = self.db_info.getvi('num_items')
        if self.num_items is None:
            self.num_items = 0
            self.db_info.setvi('num_items', self.num_items)

    def __del__(self):
        self.db_keys.close()
        self.db_vals.close()
        self.db_info.close()
        self.env.close()

    def add(self, codes, keys):
        key = "%08d" % self.num_items

        self.db_keys.set(key, pickle.dumps(keys, protocol=2))
        self.db_vals.set(key, pickle.dumps(codes, protocol=2))

        self.num_items += codes.shape[0]
        self.db_info.setvi('num_items', self.num_items)

    def clear(self):
        with self.env.begin(write=True) as txt:
            txt.drop(self.db_keys.db, False)
            txt.drop(self.db_vals.db, False)
            txt.drop(self.db_info.db, False)

    def __iter__(self):
        self.iter_txt = self.env.begin()
        self.cursor_keys = self.iter_txt.cursor(self.db_keys.db)
        self.cursor_vals = self.iter_txt.cursor(self.db_vals.db)
        return self

    def next(self):
        status_keys = self.cursor_keys.next()
        status_vals = self.cursor_vals.next()
        if status_keys and status_vals:
            keys = pickle.loads(self.cursor_keys.value())
            vals = pickle.loads(self.cursor_vals.value())
            return keys, vals
        else:
            # self.iter_txt.close()
            raise StopIteration


PQ_DIC = {
    'mem':  MemPQStorage,
    'lmdb': LMDBPQStorage,
}
