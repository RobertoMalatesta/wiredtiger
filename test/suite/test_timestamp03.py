#!/usr/bin/env python
#
# Public Domain 2014-2017 MongoDB, Inc.
# Public Domain 2008-2014 WiredTiger, Inc.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# test_timestamp03.py
#   Timestamps: checkpoints
#

from helper import copy_wiredtiger_home
import random
from suite_subprocess import suite_subprocess
import wiredtiger, wttest
from wtscenario import make_scenarios

def timestamp_str(t):
    return '%x' % t

def timestamp_ret_str(t):
    s = timestamp_str(t)
    if len(s) % 2 == 1:
        s = '0' + s
    return s

class test_timestamp03(wttest.WiredTigerTestCase, suite_subprocess):
    table_ts_log     = 'ts03_ts_logged'
    table_ts_nolog   = 'ts03_ts_nologged'
    table_nots_log   = 'ts03_nots_logged'
    table_nots_nolog = 'ts03_nots_nologged'

    types = [
        ('file', dict(uri='file:', use_cg=False, use_index=False)),
        ('lsm', dict(uri='lsm:', use_cg=False, use_index=False)),
        ('table-cg', dict(uri='table:', use_cg=True, use_index=False)),
        ('table-index', dict(uri='table:', use_cg=False, use_index=True)),
        ('table-simple', dict(uri='table:', use_cg=False, use_index=False)),
    ]

    ckpt = [
        ('use_ts_def', dict(ckptcfg='', val='none')),
        ('use_ts_false', dict(ckptcfg='use_timestamp=false', val='all')),
        ('use_ts_true', dict(ckptcfg='use_timestamp=true', val='none')),
        ('read_ts', dict(ckptcfg='read_timestamp', val='none')),
    ]

    conncfg = [
        ('nolog', dict(conn_config='create', using_log=False)),
        ('V1', dict(conn_config='create,log=(enabled),compatibility=(release="2.9")', using_log=True)),
        ('V2', dict(conn_config='create,log=(enabled)', using_log=True)),
    ]

    scenarios = make_scenarios(types, ckpt, conncfg)

    # Binary values.
    value  = u'\u0001\u0002abcd\u0003\u0004'
    value2 = u'\u0001\u0002dcba\u0003\u0004'
    value3 = u'\u0001\u0002cdef\u0003\u0004'
    value4 = u'\u0001\u0002fedc\u0003\u0004'

    # Check that a cursor (optionally started in a new transaction), sees the
    # expected values.
    def check(self, session, txn_config, tablename, expected):

        if txn_config:
            session.begin_transaction(txn_config)

        cur = session.open_cursor(self.uri + tablename, None)
        actual = dict((k, v) for k, v in cur if v != 0)
        self.assertEqual(actual, expected)
        # Search for the expected items as well as iterating
        for k, v in expected.iteritems():
            self.assertEqual(cur[k], v, "for key " + str(k))
        cur.close()
        if txn_config:
            session.commit_transaction()
    #
    # Take a backup of the database and verify that the value we want to
    # check exists in the tables the expected number of times.
    #
    def backup_check(
        self, check_value, exp_ts_log_cnt, exp_ts_nolog_cnt, exp_nots_log_cnt,
        exp_nots_nolog_cnt
    ):
        newdir = "BACKUP"
        copy_wiredtiger_home('.', newdir, True)

        conn = self.setUpConnectionOpen(newdir)
        session = self.setUpSessionOpen(conn)
        cur_ts_log      = session.open_cursor(self.uri + self.table_ts_log, None)
        cur_ts_nolog    = session.open_cursor(self.uri + self.table_ts_nolog, None)
        cur_nots_log    = session.open_cursor(self.uri + self.table_nots_log, None)
        cur_nots_nolog  = session.open_cursor(self.uri + self.table_nots_nolog, None)
        # Count how many times the check_value is present in the
        # logged timestamp table.
        act_ts_log_cnt = 0
        for k, v in cur_ts_log:
            if check_value in str(v):
                act_ts_log_cnt += 1
        cur_ts_log.close()
        # Count how many times the check_value is present in the
        # not logged timestamp table
        act_ts_nolog_cnt = 0
        for k, v in cur_ts_nolog:
            if check_value in str(v):
                # print "check_value found in key " + str(k)
                act_ts_nolog_cnt += 1
        cur_ts_nolog.close()
        # Count how many times the check_value is present in the
        # logged non-timestamp table.
        act_nots_log_cnt = 0
        for k, v in cur_nots_log:
            if check_value in str(v):
                # print "check_value found in key " + str(k)
                act_nots_log_cnt += 1
        cur_nots_log.close()
        # Count how many times the check_value is present in the
        # not logged non-timestamp table.
        act_nots_nolog_cnt = 0
        for k, v in cur_nots_nolog:
            if check_value in str(v):
                act_nots_nolog_cnt += 1
        cur_nots_nolog.close()
        conn.close()
        # print "CHECK BACKUP: act_ts_log_cnt " + str(act_ts_log_cnt)
        # print "CHECK BACKUP: exp_ts_log_cnt " + str(exp_ts_log_cnt)
        # print "CHECK BACKUP: act_ts_nolog_cnt " + str(act_ts_nolog_cnt)
        # print "CHECK BACKUP: exp_ts_nolog_cnt " + str(exp_ts_nolog_cnt)
        # print "CHECK BACKUP: act_nots_log_cnt " + str(act_nots_log_cnt)
        # print "CHECK BACKUP: exp_nots_log_cnt " + str(exp_nots_log_cnt)
        # print "CHECK BACKUP: act_nots_nolog_cnt " + str(act_nots_nolog_cnt)
        # print "CHECK BACKUP: exp_nots_nolog_cnt " + str(exp_nots_nolog_cnt)
        # print "CHECK BACKUP: config " + str(self.ckptcfg)
        self.assertEqual(act_ts_log_cnt, exp_ts_log_cnt)
        self.assertEqual(act_ts_nolog_cnt, exp_ts_nolog_cnt)
        self.assertEqual(act_nots_log_cnt, exp_nots_log_cnt)
        self.assertEqual(act_nots_nolog_cnt, exp_nots_nolog_cnt)

    # Check that a cursor sees the expected values after a checkpoint.
    def ckpt_backup(
        self, check_value, val_ts_log_cnt, val_ts_nolog_cnt, val_nots_log_cnt,
        val_nots_nolog_cnt, ckptts
    ):

        # Take a checkpoint.  Make a copy of the database.  Open the
        # copy and verify whether or not the expected data is in there.
        self.pr("CKPT: " + self.ckptcfg)
        ckptcfg = self.ckptcfg
        if not ckptts:
            if ckptcfg == 'read_timestamp':
                ckptcfg = self.ckptcfg + '=' + self.oldts
        else:
            ckptcfg = ckptts
        # print "CKPT: " + ckptcfg

        self.session.checkpoint(ckptcfg)
        self.backup_check(check_value, val_ts_log_cnt, val_ts_nolog_cnt,
            val_nots_log_cnt, val_nots_nolog_cnt)

    def test_timestamp03(self):
        if not wiredtiger.timestamp_build():
            self.skipTest('requires a timestamp build')

        uri_ts_log      = self.uri + self.table_ts_log
        uri_ts_nolog    = self.uri + self.table_ts_nolog
        uri_nots_log    = self.uri + self.table_nots_log
        uri_nots_nolog  = self.uri + self.table_nots_nolog
        #
        # Open four tables:
        # 1. Table is logged and uses timestamps.
        # 2. Table is not logged and uses timestamps.
        # 3. Table is logged and does not use timestamps.
        # 4. Table is not logged and does not use timestamps.
        #
        self.session.create(uri_ts_log, 'key_format=i,value_format=S')
        cur_ts_log = self.session.open_cursor(uri_ts_log)
        self.session.create(uri_ts_nolog, 'key_format=i,value_format=S,log=(enabled=false)')
        cur_ts_nolog = self.session.open_cursor(uri_ts_nolog)
        self.session.create(uri_nots_log, 'key_format=i,value_format=S')
        cur_nots_log = self.session.open_cursor(uri_nots_log)
        self.session.create(uri_nots_nolog, 'key_format=i,value_format=S, log=(enabled=false)')
        cur_nots_nolog = self.session.open_cursor(uri_nots_nolog)

        # Insert keys 1..100 each with timestamp=key, in some order
        nkeys = 100
        orig_keys = range(1, nkeys+1)
        keys = orig_keys[:]
        random.shuffle(keys)

        for k in keys:
            cur_nots_log[k] = self.value
            cur_nots_nolog[k] = self.value
            self.session.begin_transaction()
            cur_ts_log[k] = self.value
            cur_ts_nolog[k] = self.value
            self.session.commit_transaction('commit_timestamp=' + timestamp_str(k))

        # Scenario: 1
        # Check that we see all the inserted values as per transaction
        # visibility when reading with out the read_timestamp.
        # All tables should see all the values.
        self.check(self.session, "", self.table_ts_log,
            dict((k, self.value) for k in orig_keys))
        self.check(self.session, "", self.table_ts_nolog,
            dict((k, self.value) for k in orig_keys))
        self.check(self.session, "", self.table_nots_log,
            dict((k, self.value) for k in orig_keys))
        self.check(self.session, "", self.table_nots_nolog,
            dict((k, self.value) for k in orig_keys))

        # Scenario: 2
        # Check that we see the inserted values as per the timestamp.
        for i, t in enumerate(orig_keys):
            # Tables using the timestamps should see the values as per the
            # given read_timestamp
            self.check(self.session, 'read_timestamp=' + timestamp_str(t),
                self.table_ts_log, dict((k, self.value) for k in orig_keys[:i+1]))
            self.check(self.session, 'read_timestamp=' + timestamp_str(t),
                self.table_ts_nolog, dict((k, self.value) for k in orig_keys[:i+1]))
            # Tables not using the timestamps should see all the values.
            self.check(self.session, 'read_timestamp=' + timestamp_str(t),
                self.table_nots_log, dict((k, self.value) for k in orig_keys))
            self.check(self.session, 'read_timestamp=' + timestamp_str(t),
                self.table_nots_nolog, dict((k, self.value) for k in orig_keys))

        # Bump the oldest_timestamp, we're not going back...
        self.assertEqual(self.conn.query_timestamp(), timestamp_ret_str(100))
        self.oldts = timestamp_str(100)
        self.conn.set_timestamp('oldest_timestamp=' + self.oldts)
        self.conn.set_timestamp('stable_timestamp=' + self.oldts)
        # print "Oldest " + self.oldts

        # Scenario: 3
        # Check that we see all the data values after moving the oldest_timestamp
        # to the current timestamp
        # All tables should see all the values.
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_ts_log, dict((k, self.value) for k in orig_keys))
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_ts_nolog, dict((k, self.value) for k in orig_keys))
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_nots_log, dict((k, self.value) for k in orig_keys))
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_nots_nolog, dict((k, self.value) for k in orig_keys))

        # Update the keys and checkpoint using the stable_timestamp.
        random.shuffle(keys)
        count = 0
        for k in keys:
            # Make sure a timestamp cursor is the last one to update.  This
            # tests the scenario for a bug we found where recovery replayed
            # the last record written into the log.
            #
            # print "Key " + str(k) + " to value2"
            cur_nots_log[k] = self.value2
            cur_nots_nolog[k] = self.value2
            self.session.begin_transaction()
            cur_ts_log[k] = self.value2
            cur_ts_nolog[k] = self.value2
            ts = timestamp_str(k + 100)
            self.session.commit_transaction('commit_timestamp=' + ts)
            # print "Commit key " + str(k) + " ts " + ts
            count += 1
        # print "Updated " + str(count) + " keys to value2"

        # Scenario: 4
        # Check that we don't see the updated data of timestamp tables
        # with the read_timestamp as oldest_timestamp
        # Tables using the timestamps should see old values (i.e. value) only
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_ts_log, dict((k, self.value) for k in orig_keys))
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_ts_nolog, dict((k, self.value) for k in orig_keys))
        # Tables not using the timestamps should see updated values (i.e. value2).
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_nots_log, dict((k, self.value2) for k in orig_keys))
        self.check(self.session, 'read_timestamp=' + self.oldts,
            self.table_nots_nolog, dict((k, self.value2) for k in orig_keys))

        # Scenario: 5
        # Check that we see the updated values as per the timestamp.
        # Construct expected values.
        expected_dict = dict((k, self.value) for k in orig_keys)
        for i, t in enumerate(orig_keys):
            # update expected value
            expected_dict[i+1] = self.value2
            # Tables using the timestamps should see the updated values as per
            # the given read_timestamp
            self.check(self.session, 'read_timestamp=' + timestamp_str(t + 100),
                self.table_ts_log, expected_dict)
            self.check(self.session, 'read_timestamp=' + timestamp_str(t + 100),
                self.table_ts_nolog, expected_dict)
            # Tables not using the timestamps should see all the data values as
            # updated values (i.e. value2).
            self.check(self.session, 'read_timestamp=' + timestamp_str(t + 100),
                self.table_nots_log, dict((k, self.value2) for k in orig_keys))
            self.check(self.session, 'read_timestamp=' + timestamp_str(t + 100),
                self.table_nots_nolog, dict((k, self.value2) for k in orig_keys))

        # Take a checkpoint using the given configuration.  Then verify
        # whether value2 appears in a copy of that data or not.
        val_ts_log_cnt = val_nots_log_cnt = val_nots_nolog_cnt = nkeys
        if self.val == 'all':
            # if use_timestamp is false, then all updates will be checkpointed.
            val_ts_nolog_cnt = nkeys
        else:
            val_ts_nolog_cnt = 0
        self.ckpt_backup(self.value2, val_ts_log_cnt, val_ts_nolog_cnt,
            val_nots_log_cnt, val_nots_nolog_cnt, "")
        if self.ckptcfg != 'read_timestamp':
            # Update the stable_timestamp to the latest, but not the
            # oldest_timestamp and make sure we can see the data.  Once the
            # stable_timestamp is moved we should see all keys with value2.
            self.conn.set_timestamp('stable_timestamp=' + \
                timestamp_str(100+nkeys))
            self.ckpt_backup(self.value2, nkeys, nkeys, nkeys, nkeys, "")

        # Scenario: 6
        # Update the keys and checkpoint using the stable_timestamp and
        # the read_timestamp.
        random.shuffle(keys)
        count = 0
        for k in keys:
            # Make sure a timestamp cursor is the last one to update.
            #
            # print "Key " + str(k) + " to value3"
            cur_nots_log[k] = self.value3
            cur_nots_nolog[k] = self.value3
            self.session.begin_transaction()
            cur_ts_log[k] = self.value3
            cur_ts_nolog[k] = self.value3
            ts = timestamp_str(k + 200)
            self.session.commit_transaction('commit_timestamp=' + ts)
            # print "Commit key " + str(k) + " ts " + ts
            count += 1
        # print "Updated " + str(count) + " keys to value3"

        # make the read_timestamp != stable_timestamp, take checkpoints using
        # both the stable_timestamp and the read_timestamp and check that we
        # see different data.
        if self.ckptcfg == 'use_timestamp=true':
            # make sure the stable_timestamp is set.
            ckpt_ts = 'stable_timestamp=' + timestamp_str(100 + nkeys)
            self.conn.set_timestamp('stable_timestamp=' + timestamp_str(100 + nkeys))
            # Check that we see the data values as per the stable_timestamp.
            # Tables not using the timestamps should see all data values as
            # updated value (i.e. value3)
            # Table using the timestamps and logged should also see all data values
            # as updated value (i.e. value3)
            val_nots_log_cnt = val_ts_log_cnt = val_nots_nolog_cnt = nkeys
            # Table using the timestamps and not logged should not see any
            # data value as updated value (i.e. value3)
            val_ts_nolog_cnt = 0
            self.ckpt_backup(self.value3, val_ts_log_cnt, val_ts_nolog_cnt,
                val_nots_log_cnt, val_nots_nolog_cnt, "")

            # Check that we see the data values as per the read_timestamp but
            # not as per the stable_timestamp.
            # All Tables should see all data values as updated value (i.e. value3)
            ckpt_ts = 'read_timestamp=' + timestamp_str(200 + nkeys)
            val_ts_nolog_cnt = nkeys
            self.ckpt_backup(self.value3, val_ts_log_cnt, val_ts_nolog_cnt,
                val_nots_log_cnt, val_nots_nolog_cnt, ckpt_ts)

        # If we're not using the log we're done.
        if not self.using_log:
            return

        # Scenario: 7
        # Update the keys and log_flush with out checkpoint.
        random.shuffle(keys)
        count = 0
        for k in keys:
            # Make sure a timestamp cursor is the last one to update.
            #
            # print "Key " + str(k) + " to value4"
            cur_nots_log[k] = self.value4
            cur_nots_nolog[k] = self.value4
            self.session.begin_transaction()
            cur_ts_log[k] = self.value4
            cur_ts_nolog[k] = self.value4
            ts = timestamp_str(k + 300)
            self.session.commit_transaction('commit_timestamp=' + ts)
            # print "Commit key " + str(k) + " ts " + ts
            count += 1
        # print "Updated " + str(count) + " keys to value4"

        # Flush the log but don't checkpoint
        self.session.log_flush('sync=on')

        # Take a backup and then verify whether value4 appears in a copy
        # of that data or not.  Both tables that are logged should see
        # all the data regardless of timestamps.  Both tables that are not
        # logged should not see any of it.
        val_ts_nolog_cnt = val_nots_nolog_cnt = 0
        val_ts_log_cnt = val_nots_log_cnt = nkeys
        self.backup_check(self.value4, val_ts_log_cnt, val_ts_nolog_cnt,
            val_nots_log_cnt, val_nots_nolog_cnt)

if __name__ == '__main__':
    wttest.run()
