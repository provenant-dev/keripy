# -*- encoding: utf-8 -*-
"""
keri.db.dbing module


import lmdb
db = lmdb.open("/tmp/keri_db_setup_test")
db.max_key_size()
511

# create named dbs  (core and tables)
    gDbEnv.open_db(b'core')
    gDbEnv.open_db(b'hid2did')  # table of dids keyed by hids
    gDbEnv.open_db(b'did2offer', dupsort=True)  # table of offer expirations keyed by offer relative dids
    gDbEnv.open_db(b'anon', dupsort=True)  # anonymous messages
    gDbEnv.open_db(b'expire2uid', dupsort=True)  # expiration to uid anon

The dupsort, integerkey, integerdup, and dupfixed parameters are ignored
if the database already exists.
The state of those settings are persistent and immutable per database.
See _Database.flags() to view the state of those options for an opened database.
A consequence of the immutability of these flags is that the default non-named
database will never have these flags set.

So only need to set dupsort first time opened each other opening does not
need to call it


May want to use buffers for reads of immutable serializations such as events
and sigs. Anything not read modify write but read only.

"{:032x}".format(1024)
'00000000000000000000000000000400'

h = ["00", "01", "02", "0a", "0f", "10", "1a", "11", "1f", "f0", "a0"]
h.sort()
h
['00', '01', '02', '0a', '0f', '10', '11', '1a', '1f', 'a0', 'f0']

l
['a', 'aa', 'b', 'ba', 'aaa', 'baa']
l.sort()
l
['a', 'aa', 'aaa', 'b', 'ba', 'baa']

"""

import os
import shutil
import stat
from collections import abc
from contextlib import contextmanager
from typing import Union

import lmdb
from ordered_set import OrderedSet as oset
from hio.base import filing

import keri
from ..kering import MaxON  # maximum ordinal number for seqence or first seen
from ..help import helping

ProemSize = 32  # does not include trailing separator
MaxProem = int("f"*(ProemSize), 16)
SuffixSize = 32  # does not include trailing separator
MaxSuffix = int("f"*(SuffixSize), 16)

def onKey(top, on, *, sep=b'.'):
    """
    Returns:
        onkey (bytes): key formed by joining top key and hex str conversion of
                       int ordinal number on with sep character.

    Parameters:
        top (str | bytes): top key prefix to be joined with hex version of on using sep
        on (int): ordinal number to be converted to 32 hex bytes
        sep (bytes): separator character for join

    """
    if hasattr(top, "encode"):
        top = top.encode("utf-8")  # convert str to bytes
    return (b'%s%s%032x' % (top, sep, on))


def snKey(pre, sn):
    """
    Returns:
        snkey (bytes): key formed by joining pre and hex str conversion of int
                       sequence ordinal number sn with sep character b".".

    Parameters:
        pre (str | bytes): key prefix to be joined with hex version of on using
                           b"." sep
        sn (int): sequence number to be converted to 32 hex bytes
    """
    return onKey(pre, sn, sep=b'.')


def fnKey(pre, fn):
    """
    Returns:
        fnkey (bytes): key formed by joining pre and hex str conversion of int
                       first seen ordinal number fn with sep character b".".

    Parameters:
        pre (str | bytes): key prefix to be joined with hex version of on using
                           b"." sep
        fn (int): first seen ordinal number to be converted to 32 hex bytes
    """
    return onKey(pre, fn, sep=b'.')


def dgKey(pre, dig):
    """
    Returns bytes DB key from concatenation of '.' with qualified Base64 prefix
    bytes pre and qualified Base64 bytes digest of serialized event
    If pre or dig are str then converts to bytes
    """
    if hasattr(pre, "encode"):
        pre = pre.encode("utf-8")  # convert str to bytes
    if hasattr(dig, "encode"):
        dig = dig.encode("utf-8")  # convert str to bytes
    return (b'%s.%s' %  (pre, dig))


def dtKey(pre, dts):
    """
    Returns bytes DB key from concatenation of '|' qualified Base64 prefix
    bytes pre and bytes dts datetime string of extended tz aware ISO8601
    datetime of event

    '2021-02-13T19:16:50.750302+00:00'

    """
    if hasattr(pre, "encode"):
        pre = pre.encode("utf-8")  # convert str to bytes
    if hasattr(dts, "encode"):
        dts = dts.encode("utf-8")  # convert str to bytes
    return (b'%s|%s' % (pre, dts))

# ToDo right split so key prefix could be top of key space with more than one
# part
def splitKey(key, sep=b'.'):
    """
    Returns duple of pre and either dig or on, sn, fn str or dts datetime str by
    splitting key at bytes sep
    Accepts either bytes or str key and returns same type
    Raises ValueError if key does not split into exactly two elements

    Parameters:
       key is database key with split at sep
       sep is bytes separator character. default is b'.'
    """
    if isinstance(key, memoryview):
        key = bytes(key)
    if hasattr(key, "encode"):  # str not bytes
        if hasattr(sep, 'decode'):  # make sep match bytes or str
            sep = sep.decode("utf-8")
    else:
        if hasattr(sep, 'encode'):  # make sep match bytes or str
            sep = sep.encode("utf-8")
    splits = key.rsplit(sep, 1)
    if len(splits) != 2:
        raise  ValueError(f"Unsplittable {key=} at {sep=}.")
    return tuple(splits)


def splitOnKey(key, *, sep=b'.'):
    """
    Returns list of pre and int on from key
    Accepts either bytes or str key
    ordinal number  appears in key in hex format
    """
    if isinstance(key, memoryview):
        key = bytes(key)
    top, on = splitKey(key, sep=sep)
    on = int(on, 16)
    return (top, on)


splitSnKey = splitOnKey  # alias so intent is clear, sn vs fn
splitFnKey = splitOnKey  # alias so intent is clear, sn vs fn

splitKeyON = splitOnKey  # backwards compatible alias
splitKeySN = splitSnKey  # backwards compatible alias
splitKeyFN = splitFnKey  # backwards compatible alias


def splitKeyDT(key):
    """
    Returns list of pre and dts converted to datetime from key
    dts is TZ aware Iso8601 '2021-02-13T19:16:50.750302+00:00'

    Accepts either bytes or str key
    """
    if isinstance(key, memoryview):
        key = bytes(key)
    pre, dts = splitKey(key, sep=b'|')
    if hasattr(dts, "decode"):
        dts = dts.decode("utf-8")
    dt = helping.fromIso8601(dts)
    return (pre, dt)


def suffix(key: Union[bytes, str, memoryview], ion: int, *, sep: Union[bytes, str]=b'.'):
    """
    Returns:
       iokey (bytes): actual DB key after concatenating suffix as hex version
       of insertion ordering ordinal int ion using separator sep.

    Parameters:
        key (Union[bytes, str]): apparent effective database key (unsuffixed)
        ion (int)): insertion ordering ordinal for set of vals
        sep (bytes): separator character(s) for concatenating suffix
    """
    if isinstance(key, memoryview):
        key = bytes(key)
    elif hasattr(key, "encode"):
        key = key.encode("utf-8")  # encode str to bytes
    if hasattr(sep, "encode"):
        sep = sep.encode("utf-8")
    ion =  b"%032x" % ion
    return sep.join((key, ion))


def unsuffix(iokey: Union[bytes, str, memoryview], *, sep: Union[bytes, str]=b'.'):
    """
    Returns:
       result (tuple): (key, ion) by splitting iokey at rightmost separator sep
            strip off suffix, where key is bytes apparent effective DB key and
            ion is the insertion ordering int converted from stripped of hex
            suffix

    Parameters:
        iokey (Union[bytes, str]): apparent effective database key (unsuffixed)
        sep (bytes): separator character(s) for concatenating suffix
    """
    if isinstance(iokey, memoryview):
        iokey = bytes(iokey)
    elif hasattr(iokey, "encode"):
        iokey = iokey.encode("utf-8")  # encode str to bytes
    if hasattr(sep, "encode"):
        sep = sep.encode("utf-8")
    key, ion = iokey.rsplit(sep=sep, maxsplit=1)
    ion = int(ion, 16)
    return (key, ion)


def clearDatabaserDir(path):
    """
    Remove directory path
    """
    if os.path.exists(path):
        shutil.rmtree(path)


@contextmanager
def openLMDB(*, cls=None, name="test", temp=True, **kwa):
    """
    Context manager wrapper LMDBer instances.
    Defaults to temporary databases.
    Context 'with' statements call .close on exit of 'with' block

    Parameters:
        cls is Class instance of subclass instance
        name is str name of LMDBer dirPath so can have multiple databasers
             at different directory path names thar each use different name
        temp is Boolean, True means open in temporary directory, clear on close
                        Otherwise open in persistent directory, do not clear on close

    Usage:

    with openDatabaser(name="gen1") as baser1:
        baser1.env  ....

    with openDatabaser(name="gen2, cls=Baser)

    wl.close(clear=True if wl.temp else False)

    """
    lmdber = None
    if cls is None:
        cls = LMDBer
    try:
        lmdber = cls(name=name, temp=temp, reopen=True, **kwa)
        yield lmdber

    finally:
        if lmdber:
            lmdber.close(clear=lmdber.temp)  # clears if lmdber.temp


class LMDBer(filing.Filer):
    """
    LBDBer base class for LMDB manager instances.
    Creates a specific instance of an LMDB database directory and environment.

    Attributes:  (inherited)
        name (str): unique path component used in directory or file path name
        base (str): another unique path component inserted before name
        temp (bool): True means use /tmp directory
        headDirPath is head directory path
        path is full directory path
        perm is numeric os permissions for directory and/or file(s)
        filed (bool): True means .path ends in file.
                       False means .path ends in directory
        mode (str): file open mode if filed
        fext (str): file extension if filed
        file (File)
        opened is Boolean, True means directory created and if file then file
                is opened. False otherwise

    Attributes:
        env (lmdb.env): LMDB main (super) database environment
        readonly (bool): True means open LMDB env as readonly

    Properties:

    File/Directory Creation Mode Notes:
        .Perm provides default restricted access permissions to directory and/or files
        stat.S_ISVTX | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR
        0o1700==960

        stat.S_ISVTX  is Sticky bit. When this bit is set on a directory it means
            that a file in that directory can be renamed or deleted only by the
            owner of the file, by the owner of the directory, or by a privileged process.
            When this bit is set on a file it means nothing
        stat.S_IRUSR Owner has read permission.
        stat.S_IWUSR Owner has write permission.
        stat.S_IXUSR Owner has execute permission.
    """
    HeadDirPath = "/usr/local/var"  # default in /usr/local/var
    TailDirPath = "keri/db"
    CleanTailDirPath = "keri/clean/db"
    AltHeadDirPath = "~"  # put in ~ as fallback when desired not permitted
    AltTailDirPath = ".keri/db"
    AltCleanTailDirPath = ".keri/clean/db"
    TempHeadDir = "/tmp"
    TempPrefix = "keri_lmdb_"
    TempSuffix = "_test"
    Perm = stat.S_ISVTX | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR  # 0o1700==960
    MaxNamedDBs = 96
    MapSize = 104857600

    def __init__(self, readonly=False, **kwa):
        """
        Setup main database directory at .dirpath.
        Create main database environment at .env using .path.

        Parameters:
            name (str): directory path name differentiator directory/file
                When system employs more than one keri installation, name allows
                differentiating each instance by name
            base (str): optional directory path segment inserted before name
                that allows further differentiation with a hierarchy. "" means
                optional.
            temp (bool): assign to .temp
                True then open in temporary directory, clear on close
                Otherwise then open persistent directory, do not clear on close
            headDirPath (str): optional head directory pathname for main database
                Default .HeadDirPath
            mode (int): optional numeric os dir permissions for database
                directory and database files. Default .DirMode
            reopen (bool): True means (re)opened by this init
                           False  means not (re)opened by this init but later
            clear (bool): True means remove directory upon close if reopon
                          False means do not remove directory upon close if reopen
            reuse (bool): True means reuse self.path if already exists
                          False means do not reuse but remake self.path
            clean (bool): True means path uses clean tail variant
                             False means path uses normal tail variant
            filed (bool): True means .path is file path not directory path
                          False means .path is directory path not file path
            mode (str): File open mode when filed
            fext (str): File extension when filed

            readonly (bool): True means open database in readonly mode
                                False means open database in read/write mode

        """

        self.env = None
        self._version = None
        self.readonly = True if readonly else False
        super(LMDBer, self).__init__(**kwa)

    def reopen(self, readonly=False, **kwa):
        """
        Open if closed or close and reopen if opened or create and open if not
        if not preexistent, directory path for lmdb at .path and then
        Open lmdb and assign to .env

        Parameters:
            temp (bool): assign to .temp
                         True means open in temporary directory, clear on close
                         False means open persistent directory, do not clear on close
            headDirPath (str): optional head directory pathname for main database
                               Default .HeadDirpath
            perm (int): optional numeric os dir permissions for database
                         directory and database files. Default .Perm
            clear (bool): True means remove directory upon close
                             False means do not remove directory upon close
            reuse (bool): True means reuse self.path if already exists
                             False means do not reuse but remake self.path
            clean (bool): True means path uses clean tail variant
                             False means path uses normal tail variant
            mode (str): file open mode when .filed
            fext (str): File extension when .filed
            readonly (bool): True means open database in readonly mode
                                False means open database in read/write mode
        """
        exists = self.exists(name=self.name, base=self.base)
        opened = super(LMDBer, self).reopen(**kwa)
        if readonly is not None:
            self.readonly = readonly

        # open lmdb major database instance
        # creates files data.mdb and lock.mdb in .dbDirPath
        self.env = lmdb.open(self.path, max_dbs=self.MaxNamedDBs, map_size=self.MapSize,
                             mode=self.perm, readonly=self.readonly)

        self.opened = True if opened and self.env else False

        if self.opened and not self.readonly and (not exists or self.temp):
            self.version = keri.__version__

        return self.opened

    @property
    def version(self):
        """ Return the version of database stored in __version__ key.

        This value is read through cached in memory

        Returns:
            str: the version of the database or None if not set in the database

        """
        if self._version is None:
            self._version = self.getVer()

        return self._version

    @version.setter
    def version(self, val):
        """  Set the version of the database in memory and in the __version__ key

        Parameters:
            val (str): The new semver formatted version of the database

        """
        if hasattr(val, "decode"):
            val = val.decode("utf-8")  # convert bytes to str

        self._version = val
        self.setVer(self._version)

    def close(self, clear=False):
        """
        Close lmdb at .env and if clear or .temp then remove lmdb directory at .path
        Parameters:
           clear is boolean, True means clear lmdb directory
        """
        if self.env:
            try:
                self.env.close()
            except:
                pass

        self.env = None

        return super(LMDBer, self).close(clear=clear)

    def getVer(self):
        """ Returns the value of the the semver formatted version in the __version__ key in this database

        Returns:
            str: semver formatted version of the database

        """
        with self.env.begin() as txn:
            cursor = txn.cursor()
            version = cursor.get(b'__version__')
            return version.decode("utf-8") if version is not None else None

    def setVer(self, val):
        """  Set the version of the database in the __version__ key

        Parameters:
            val (str): The new semver formatted version of the database

        """
        if hasattr(val, "encode"):
            val = val.encode("utf-8")  # convert str to bytes

        with self.env.begin(write=True) as txn:
            cursor = txn.cursor()
            cursor.replace(b'__version__', val)

    # For subdbs with no duplicate values allowed at each key. (dupsort==False)
    def putVal(self, db, key, val):
        """
        Write serialized bytes val to location key in db
        Does not overwrite.
        Returns True If val successfully written Else False
        Returns False if val at key already exitss

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
            val is bytes of value to be written
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return (txn.put(key, val, overwrite=False))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def setVal(self, db, key, val):
        """
        Write serialized bytes val to location key in db
        Overwrites existing val if any
        Returns True If val successfully written Else False

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
            val is bytes of value to be written
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return (txn.put(key, val))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def getVal(self, db, key):
        """
        Return val at key in db
        Returns None if no entry at key

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace

        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            try:
                return(txn.get(key))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def delVal(self, db, key):
        """
        Deletes value at key in db.
        Returns True If key exists in database Else False

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return (txn.delete(key))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def cnt(self, db):
        """
        Return count of values in db, or zero otherwise

        Parameters:
            db is opened named sub db with dupsort=True
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            count = 0
            for _, _ in cursor:
                count += 1
            return count

    # Suber subclasses don't need this since they always split keys int tuple to return
    def getAllItemIter(self, db, key=b'', split=True, sep=b'.'):
        """
        Returns iterator of item duple (key, val), at each key over all
        keys in db. If split is true then the key is split at sep and instead
        of returing duple it results tuple with one entry for each key split
        as well as the value.

        Works for both dupsort==False and dupsort==True

        Raises StopIteration Error when empty.

        Parameters:
            db is opened named sub db with dupsort=False
            key is key location in db to resume replay,
                   If empty then start at first key in database
            split (bool): True means split key at sep before returning
            sep (bytes): separator char for key
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if not cursor.set_range(key):  #  moves to val at key >= key, first if empty
                return  # no values end of db

            for key, val in cursor.iternext():  # return key, val at cursor
                if split:
                    splits = bytes(key).split(sep)
                    splits.append(val)
                else:
                    splits = (bytes(key), val)
                yield tuple(splits)


    def getTopItemIter(self, db, top=b''):
        """
        Iterates over branch of db given by top key

        Returns:
            items (abc.Iterator): iterator of (full key, val) tuples over a
                branch of the db given by top key where: full key is full database
                key for val not truncated top key

        Works for both dupsort==False and dupsort==True
        Because cursor.iternext() advances cursor after returning item its safe
        to delete the item within the iteration loop.

        Raises StopIteration Error when empty.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            top (bytes): truncated top key, a key space prefix to get all the items
                        from multiple branches of the key space. If top key is
                        empty then gets all items in database.
                        In Python str.startswith('') always returns True so if branch
                        key is empty string it matches all keys in db with startswith.
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if cursor.set_range(top):  # move to val at key >= key if any
                for ckey, cval in cursor.iternext():  # get key, val at cursor
                    ckey = bytes(ckey)
                    if not ckey.startswith(top): #  prev entry if any last in branch
                        break  # done
                    yield (ckey, cval)  # another entry in branch startswith key
            return  # done raises StopIteration


    def delTopVal(self, db, top=b''):
        """
        Deletes all values in branch of db given top key.

        Returns:
            result (bool): True if values were deleted at key. False otherwise
                if no values at key

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            top (bytes): truncated top key, a key space prefix to get all the items
                        from multiple branches of the key space. If top key is
                        empty then deletes all items in database

        Works for both dupsort==False and dupsort==True
        Because cursor.iternext() advances cursor after returning item its safe
        to delete the item within the iteration loop.

        Raises StopIteration Error when empty.

        """
        # when deleting can't use cursor.iternext() because the cursor advances
        # twice (skips one) once for iternext and once for delete.
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            result = False
            cursor = txn.cursor()
            if cursor.set_range(top):  # move to val at key >= key if any
                ckey, cval = cursor.item()
                while ckey:  # end of database key == b''
                    ckey = bytes(ckey)
                    if not ckey.startswith(top): #  prev entry if any last in branch
                        break  # done
                    result = cursor.delete() or result # delete moves cursor to next item
                    ckey, cval = cursor.item()  # cursor now at next item after deleted
            return result


    # For subdbs  the use keys with trailing part the is  monotonically
    # ordinal number serialized as 32 hex bytes

    def cntOnVals(self, db, key=b'', on=0, *, sep=b'.'):
        """
        Returns (int): count of of all ordinal keyed vals with top key
        but different on tail in db starting at ordinal number on of top.
        Full key is composed of top+sep+
        When dupsort==true then duplicates are included in count since .iternext
        includes duplicates.
        when key is empty then retrieves whole db

        Parameters:
            db (lmdbsubdb): named sub db of lmdb
            key (bytes): key within sub db's keyspace plus trailing part on
                         when key is empty then retrieves whole db
            on (int): ordinal number at which to initiate count
            sep (bytes): separator character for split
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if key:  # not empty
                onkey = onKey(key, on, sep=sep)  # start replay at this enty 0 is earliest
            else:
                onkey = key
            count = 0
            if not cursor.set_range(onkey):  #  moves to val at key >= key
                return count  # no values end of db

            for ckey in cursor.iternext(values=False):  # get key only at cursor
                try:
                    ckey, cn = splitOnKey(ckey, sep=sep)
                except ValueError as ex:  # not splittable key
                    break

                if key and ckey != key:  # prev is now the last event for pre
                    break  # done
                count = count+1

            return count


    def getOnItemIter(self, db, key=b'', on=0, *, sep=b'.'):
        """
        Returns iterator of triples (key, on, val), at each key over all ordinal
        numbered keys with same key + sep + on in db. Values are sorted by
        onKey(key, on) where on is ordinal number int and key is prefix sans on.
        Returned items are triples of (key, on, val)
        When dupsort==true then duplicates are included in items since .iternext
        includes duplicates.
        when key is empty then retrieves whole db

        Raises StopIteration Error when empty.

        Returns:
            items (Iterator[(key, on, val)]): triples of key, on, val

        Parameters:
            db (subdb): named sub db in lmdb
            key (bytes): key within sub db's keyspace plus trailing part on
                when key is empty then retrieves whole db
            on (int): ordinal number at which to initiate retrieval
            sep (bytes): separator character for split
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if key:  # not empty
                onkey = onKey(key, on, sep=sep)  # start replay at this enty 0 is earliest
            else:  # empty
                onkey = key
            if not cursor.set_range(onkey):  #  moves to val at key >= onkey
                return  # no values end of db raises StopIteration

            for ckey, cval in cursor.iternext():  # get key, val at cursor
                ckey, cn = splitOnKey(ckey, sep=sep)
                if key and not ckey == key:
                    break
                yield (ckey, cn, cval)



    def appendOnVal(self, db, key, val, *, sep=b'.'):
        """
        Appends val in order after last previous key with same pre in db where
        full key has key prefix and serialized on suffix attached with sep.
        Returns ordinal number in, on, of appended entry. Appended on is 1 greater
        than previous latest on at pre.
        Uses onKey(pre, on) for entries.

        Works with either dupsort==True or False since always creates new full
        key.

        Append val to end of db entries with same pre but with on incremented by
        1 relative to last preexisting entry at pre.

        Returns:
            on (int): ordinal number of newly appended val

        Parameters:
            db (subdb): named sub db in lmdb
            key (bytes): key within sub db's keyspace plus trailing part on
            val (bytes): serialized value to append
            sep (bytes): separator character for split
        """
        # set key with fn at max and then walk backwards to find last entry at pre
        # if any otherwise zeroth entry at pre
        onkey = onKey(key, MaxON, sep=sep)
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            on = 0  # unless other cases match then zeroth entry at pre
            cursor = txn.cursor()
            if not cursor.set_range(onkey):  # max is past end of database
                #  so either empty database or last is earlier pre or
                #  last is last entry  at same pre
                if cursor.last():  # not empty db. last entry earlier than max
                    ckey = cursor.key()
                    ckey, cn = splitOnKey(ckey, sep=sep)
                    if ckey == key:  # last is last entry for same pre
                        on = cn + 1  # increment
            else:  # not past end so not empty either later pre or max entry at pre
                ckey = cursor.key()
                ckey, cn = splitOnKey(ckey, sep=sep)
                if ckey == key:  # last entry for pre is already at max
                    raise ValueError(f"Number part {cn=} for key part {ckey=}"
                                     f"exceeds maximum size.")
                else:  # later pre so backup one entry
                    # either no entry before last or earlier pre with entry
                    if cursor.prev():  # prev entry, maybe same or earlier pre
                        ckey = cursor.key()
                        ckey, cn = splitOnKey(ckey, sep=sep)
                        if ckey == key:  # last entry at pre
                            on = cn + 1  # increment

            onkey = onKey(key, on, sep=sep)

            if not cursor.put(onkey, val, overwrite=False):
                raise  ValueError(f"Failed appending {val=} at {key=}.")
            return on



    # IoSet insertion order in val so can have effective dups but with
    # dupsort = False so val not limited to 511 bytes
    # For databases that support set of insertion ordered values with apparent
    # effective duplicate key but with (dupsort==False). Actual key uses hidden
    # key suffix ordinal to provide insertion ordering of value members of set
    # with same effective duplicate key.
    # Provides dupsort==True like functionality but without the associated value
    # size limitation of 511 bytes.


    def putIoSetVals(self, db, key, vals, *, sep=b'.'):
        """
        Add each val in vals to insertion ordered set of values all with the
        same apparent effective key for each val that is not already in set of
        vals at key.
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Returns:
           result (bool): True is added to set. False if already in set.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            vals (Iterable): serialized values to add to set of vals at key

        """
        result = False
        vals = oset(vals)  # make set
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            ion = 0
            iokey = suffix(key, ion, sep=sep)  # start zeroth entry if any
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                pvals = oset()  # pre-existing vals at key
                for iokey, val in cursor.iternext():  # get iokey, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey == key:
                        pvals.add(val)  # another entry at key
                        ion = cion + 1  # ion to add at is increment of cion
                    else:  # prev entry if any was the last entry for key
                        break  # done
                vals -= pvals  # remove vals already in pvals

            for i, val in enumerate(vals):
                iokey = suffix(key, ion+i, sep=sep)  # ion is at add on amount
                result = cursor.put(iokey,
                                    val,
                                    dupdata=False,
                                    overwrite=False) or result  # not short circuit
            return result


    def addIoSetVal(self, db, key, val, *, sep=b'.'):
        """
        Add val idempotently to insertion ordered set of values all with the
        same apparent effective key if val not already in set of vals at key. A
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Returns:
           result (bool): True is added to set. False if already in set.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            val (bytes): serialized value to add

        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            vals = oset()
            ion = 0
            iokey = suffix(key, ion, sep=sep)  # start zeroth entry if any
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                for iokey, cval in cursor.iternext():  # get iokey, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey == key:
                        vals.add(cval)  # another entry at key
                        ion = cion + 1 # ion to add at is increment of cion
                    else:  # prev entry if any was the last entry for key
                        break  # done

            if val in vals:  # already in set
                return False

            iokey = suffix(key, ion, sep=sep)  # ion is at add on amount
            return cursor.put(iokey, val, dupdata=False, overwrite=False)


    def appendIoSetVal(self, db, key, val, *, sep=b'.'):
        """
        Append val non-idempotently to insertion ordered set of values all with
        the same apparent effective key.  If val already in set at key then
        after append there will be multiple entries in database with val at key
        each with different insertion order (iokey).
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Works by walking backward to find last iokey for key instead of reading
        all vals for ioky.

        Returns:
           ion (int): hidden insertion ordering ordinal of appended val

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            val (bytes): value to append
        """
        ion = 0  # default is zeroth insertion at key
        iokey = suffix(key, ion=MaxSuffix, sep=sep)  # make iokey at max and walk back
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            cursor = txn.cursor()  # create cursor to walk back
            if not cursor.set_range(iokey):  # max is past end of database
                # Three possibilities for max past end of database
                # 1. last entry in db is for same key
                # 2. last entry in db is for other key before key
                # 3. database is empty
                if cursor.last():  # not 3. empty db, so either 1. or 2.
                    ckey, cion = unsuffix(cursor.key(), sep=sep)
                    if ckey == key:  # 1. last is last entry for same key
                        ion = cion + 1  # so set ion to the increment of cion
            else:  # max is not past end of database
                # Two possibilities for max not past end of databseso
                # 1. cursor at max entry at key
                # 2. other key after key with entry in database
                ckey, cion = unsuffix(cursor.key(), sep=sep)
                if ckey == key:  # 1. last entry for key is already at max
                    raise ValueError("Number part of key {} at maximum"
                                     " size.".format(ckey))
                else:  # 2. other key after key so backup one entry
                    # Two possibilities: 1. no prior entry 2. prior entry
                    if cursor.prev():  # prev entry, maybe same or earlier pre
                        # 2. prior entry with two possiblities:
                        # 1. same key
                        # 2. other key before key
                        ckey, cion = unsuffix(cursor.key(), sep=sep)
                        if ckey == key:  # prior (last) entry at key
                            ion = cion + 1  # so set ion to the increment of cion

            iokey = suffix(key, ion=ion, sep=sep)
            if not cursor.put(iokey, val, overwrite=False):
                raise  ValueError("Failed appending {} at {}.".format(val, key))

            return ion



    def setIoSetVals(self, db, key, vals, *, sep=b'.'):
        """
        Erase all vals at key and then add unique vals as insertion ordered set of
        values all with the same apparent effective key.
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Returns:
           result (bool): True is added to set.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            vals (abc.Iterable): serialized values to add to set of vals at key
        """
        self.delIoSetVals(db=db, key=key, sep=sep)
        result = False
        vals = oset(vals)  # make set
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            for i, val in enumerate(vals):
                iokey = suffix(key, i, sep=sep)  # ion is at add on amount
                result = txn.put(iokey, val, dupdata=False, overwrite=True) or result
            return result



    def getIoSetVals(self, db, key, *, ion=0, sep=b'.'):
        """
        Returns:
            ioset (oset): the insertion ordered set of values at same apparent
            effective key.
            Uses hidden ordinal key suffix for insertion ordering.
            The suffix is appended and stripped transparently.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            ion (int): starting ordinal value, default 0

        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            vals = []
            iokey = suffix(key, ion, sep=sep)  # start ion th value for key zeroth default
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                for iokey, val in cursor.iternext():  # get iokey, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey != key:  # prev entry if any was the last entry for key
                        break  # done
                    vals.append(val)  # another entry at key
            return vals


    def getIoSetValsIter(self, db, key, *, ion=0, sep=b'.'):
        """
        Returns:
            ioset (abc.Iterator): iterator over insertion ordered set of values
            at same apparent effective key.
            Uses hidden ordinal key suffix for insertion ordering.
            The suffix is appended and stripped transparently.

        Raises StopIteration Error when empty.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            ion (int): starting ordinal value, default 0
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            iokey = suffix(key, ion, sep=sep)  # start ion th value for key zeroth default
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                for iokey, val in cursor.iternext():  # get key, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey != key: #  prev entry if any was the last entry for key
                        break  # done
                    yield (val)  # another entry at key
            return  # done raises StopIteration


    def getIoSetValLast(self, db, key, *, sep=b'.'):
        """
        Returns:
            val (bytes): last added empty at apparent effective key if any,
                otherwise None if no entry

        Uses hidden ordinal key suffix for insertion ordering.
            The suffix is appended and stripped transparently.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
        """
        val = None
        ion = None  # no last value
        iokey = suffix(key, ion=MaxSuffix, sep=sep)  # make iokey at max and walk back
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()  # create cursor to walk back
            if not cursor.set_range(iokey):  # max is past end of database
                # Three possibilities for max past end of database
                # 1. last entry in db is for same key
                # 2. last entry in db is for other key before key
                # 3. database is empty
                if cursor.last():  # not 3. empty db, so either 1. or 2.
                    ckey, cion = unsuffix(cursor.key(), sep=sep)
                    if ckey == key:  # 1. last is last entry for same key
                        ion = cion  # so set ion to cion
            else:  # max is not past end of database
                # Two possibilities for max not past end of databseso
                # 1. cursor at max entry at key
                # 2. other key after key with entry in database
                ckey, cion = unsuffix(cursor.key(), sep=sep)
                if ckey == key:  # 1. last entry for key is already at max
                    ion = cion
                else:  # 2. other key after key so backup one entry
                    # Two possibilities: 1. no prior entry 2. prior entry
                    if cursor.prev():  # prev entry, maybe same or earlier pre
                        # 2. prior entry with two possiblities:
                        # 1. same key
                        # 2. other key before key
                        ckey, cion = unsuffix(cursor.key(), sep=sep)
                        if ckey == key:  # prior (last) entry at key
                            ion = cion  # so set ion to the cion

            if ion is not None:
                iokey = suffix(key, ion=ion, sep=sep)
                val = cursor.get(iokey)

            return val


    def cntIoSetVals(self, db, key, *, sep=b'.'):
        """
        Count all values with the same apparent effective key.
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Returns:
            count (int): count values in set at apparent effective key

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
        """
        return len(self.getIoSetVals(db=db, key=key, sep=sep))


    def delIoSetVals(self, db, key, *, sep=b'.'):
        """
        Deletes all values at apparent effective key.
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Returns:
            result (bool): True if values were deleted at key. False otherwise
                if no values at key

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
        """
        result = False
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            iokey = suffix(key, 0, sep=sep)  # start at zeroth value for key
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                iokey, cval = cursor.item()
                while iokey:  # end of database iokey == b'' cant internext.
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey != key:  # past key
                        break
                    result = cursor.delete() or result  # delete moves cursor to next item
                    iokey, cval = cursor.item()  # cursor now at next item after deleted
            return result


    def delIoSetVal(self, db, key, val, *, sep=b'.'):
        """
        Deletes val at apparent effective key if exists.
        Uses hidden ordinal key suffix for insertion ordering.
        The suffix is appended and stripped transparently.

        Because the insertion order of val is not provided must perform a linear
        search over set of values.

        Another problem is that vals may get added and deleted in any order so
        the max suffix ion may creep up over time. The suffix ordinal max > 2**16
        is an impossibly large number, however, so the suffix will not max out
        practically.But its not the most elegant solution.

        In some cases a better approach would be to use getIoSetItemsIter which
        returns the actual iokey not the apparent effetive key so can delete
        using the iokey without searching for the value. This is most applicable
        when processing escrows where all the escrowed items are processed linearly
        and one needs to delete some of them in stride with their processing.

        Returns:
            result (bool): True if val was deleted at key. False otherwise
                if val not found at key

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key
            val (bytes): value to delete
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            iokey = suffix(key, 0, sep=sep)  # start zeroth value for key
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                for iokey, cval in cursor.iternext():  # get iokey, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey != key:  # prev entry if any was the last entry for key
                        break  # done
                    if val == cval:
                        return cursor.delete()  # delete also moves to next so doubly moved
            return False


    def delIoSetIokey(self, db, iokey):
        """
        Deletes val at at actual iokey that includes ordinal key suffix.

        Returns:
            result (bool): True if val was deleted at iokey. False otherwise
                if no val at iokey

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            iokey (bytes): actual key with ordinal key suffix
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return txn.delete(iokey)
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{iokey}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def getIoSetItemIter(self, db, key, *, ion=0, sep=b'.'):
        """
        Returns:
            items (abc.Iterator): iterator over insertion ordered set of values
            at same apparent effective key where each iteration returns tuple
            (iokey, val). iokey includes the ordinal key suffix.
            Uses hidden ordinal key suffix for insertion ordering.
            Does not work with partial effective key.

        Raises StopIteration Error when empty.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): Apparent effective key. Does not work with partial key
                         that is not the full effective key sans the ion part.
            ion (int): starting ordinal value, default 0
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            iokey = suffix(key, ion, sep=sep)  # start ion th value for key zeroth default
            cursor = txn.cursor()
            if cursor.set_range(iokey):  # move to val at key >= iokey if any
                for iokey, val in cursor.iternext():  # get key, val at cursor
                    ckey, cion = unsuffix(iokey, sep=sep)
                    if ckey != key: #  prev entry if any was the last entry for key
                        break  # done
                    yield (iokey, val)  # another entry at key
            return  # done raises StopIteration



    # For subdbs that support duplicates at each key (dupsort==True)
    def putVals(self, db, key, vals):
        """
        Write each entry from list of bytes vals to key in db
        Adds to existing values at key if any
        Returns True If only one first written val in vals Else False
        Apparently always returns True (is this how .put works with dupsort=True)

        Duplicates are inserted in lexocographic order not insertion order.
        Lmdb does not insert a duplicate unless it is a unique value for that
        key.

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
            vals is list of bytes of values to be written
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            result = True
            try:
                for val in vals:
                    result = result and txn.put(key, val, dupdata=True)
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
            return result


    def addVal(self, db, key, val):
        """
        Add val bytes as dup to key in db
        Adds to existing values at key if any
        Returns True if written else False if dup val already exists

        Duplicates are inserted in lexocographic order not insertion order.
        Lmdb does not insert a duplicate unless it is a unique value for that
        key.

        Does inclusion test to dectect of duplicate already exists
        Uses a python set for the duplicate inclusion test. Set inclusion scales
        with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
            val is bytes of value to be written
        """
        dups = set(self.getVals(db, key))  #get preexisting dups if any
        result = False
        if val not in dups:
            with self.env.begin(db=db, write=True, buffers=True) as txn:
                try:
                    result = txn.put(key, val, dupdata=True)
                except lmdb.BadValsizeError as ex:
                    raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                                   " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
        return result


    def getVals(self, db, key):
        """
        Return list of values at key in db
        Returns empty list if no entry at key

        Duplicates are retrieved in lexocographic order not insertion order.

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            vals = []
            try:
                if cursor.set_key(key):  # moves to first_dup
                    vals = [val for val in cursor.iternext_dup()]
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
            return vals


    def getValLast(self, db, key):
        """
        Return last dup value at key in db in lexicographic order
        Returns None no entry at key
        Assumes DB opened with dupsort=True

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            val = None
            try:
                if cursor.set_key(key):  # move to first_dup
                    if cursor.last_dup(): # move to last_dup
                        val = cursor.value()
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
            return val


    def getValsIter(self, db, key):
        """
        Return iterator of all dup values at key in db
        Raises StopIteration error when done or if empty

        Duplicates are retrieved in lexocographic order not insertion order.

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            vals = []
            try:
                if cursor.set_key(key):  # moves to first_dup
                    for val in cursor.iternext_dup():
                        yield val
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def cntVals(self, db, key):
        """
        Return count of dup values at key in db, or zero otherwise

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            count = 0
            try:
                if cursor.set_key(key):  # moves to first_dup
                    count = cursor.count()
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
            return count




    def delVals(self, db, key, val=b''):
        """
        Deletes all values at key in db if val=b'' else deletes the dup
        that equals val
        Returns True If key (and val if not empty) exists in db Else False

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
            val is bytes of dup val at key to delete
        """
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return (txn.delete(key, val))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    # For subdbs that support insertion order preserving duplicates at each key.
    # IoDup class IoVals IoItems
    # dupsort==True and prepends and strips io val proem to each value.
    # because dupsort==True values are limited to 511 bytes including proem
    def putIoDupVals(self, db, key, vals):
        """
        Write each entry from list of bytes vals to key in db in insertion order
        Adds to existing values at key if any
        Returns True If at least one of vals is added as dup, False otherwise
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
            vals is list of bytes of values to be written
        """

        result = False
        dups = set(self.getIoDupVals(db, key))  #get preexisting dups if any
        with self.env.begin(db=db, write=True, buffers=True) as txn:
            idx = 0
            cursor = txn.cursor()
            try:
                if cursor.set_key(key): # move to key if any
                    if cursor.last_dup(): # move to last dup
                        idx = 1 + int(bytes(cursor.value()[:32]), 16)  # get last index as int
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")

            for val in vals:
                if val not in dups:
                    val = (b'%032x.' % (idx)) +  val  # prepend ordering proem
                    txn.put(key, val, dupdata=True)
                    idx += 1
                    result = True
        return result


    def addIoDupVal(self, db, key, val):
        """
        Add val bytes as dup in insertion order to key in db
        Adds to existing values at key if any
        Returns True if written else False if val is already a dup
        Actual value written include prepended proem ordinal
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
            val is bytes of value to be written
        """
        return self.putIoDupVals(db, key, [val])


    def getIoDupVals(self, db, key):
        """
        Return list of duplicate values at key in db in insertion order
        Returns empty list if no entry at key
        Removes prepended proem ordinal from each val  before returning
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).


        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            vals = []
            try:
                if cursor.set_key(key):  # moves to first_dup
                    # slice off prepended ordering proem
                    vals = [val[33:] for val in cursor.iternext_dup()]
                return vals
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def getIoDupValsIter(self, db, key):
        """
        Return iterator of all duplicate values at key in db in insertion order
        Raises StopIteration Error when no remaining dup items = empty.
        Removes prepended proem ordinal from each val before returning
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).


        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            vals = []
            try:
                if cursor.set_key(key):  # moves to first_dup
                    for val in cursor.iternext_dup():
                        yield val[33:]  # slice off prepended ordering proem
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def getIoDupValLast(self, db, key):
        """
        Return last added dup value at key in db in insertion order
        Returns None no entry at key
        Removes prepended proem ordinal from val before returning
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            val = None
            try:
                if cursor.set_key(key):  # move to first_dup
                    if cursor.last_dup(): # move to last_dup
                        val = cursor.value()[33:]  # slice off prepended ordering proem
                return val
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def delIoDupVals(self, db, key):
        """
        Deletes all values at key in db if key present.
        Returns True If key exists

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=True, buffers=True) as txn:
            try:
                return (txn.delete(key))
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")


    def delIoDupVal(self, db, key, val):
        """
        Deletes dup io val at key in db. Performs strip search to find match.
        Strips proems and then searches.
        Returns True if delete else False if val not present
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order
        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentially unlimited
        number of values which will be limited by memory.

        Does a linear search so not very efficient when not deleting from the front.
        This is hack for supporting escrow which needs to delete individual dup.
        The problem is that escrow is not fixed buts stuffs gets added and
        deleted which just adds to the value of the proem. 2**16 is an impossibly
        large number so the proem will not max out practically. But its not
        an elegant solution.

        Parameters:
            db is opened named sub db with dupsort=False
            key is bytes of key within sub db's keyspace
            val is bytes of value to be deleted without intersion ordering proem
        """

        with self.env.begin(db=db, write=True, buffers=True) as txn:
            cursor = txn.cursor()
            try:
                if cursor.set_key(key):  # move to first_dup
                    for proval in cursor.iternext_dup():  #  value with proem
                        if val == proval[33:]:  #  strip of proem
                            return cursor.delete()
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
        return False


    def cntIoDupVals(self, db, key):
        """
        Return count of dup values at key in db, or zero otherwise
        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            count = 0
            try:
                if cursor.set_key(key):  # moves to first_dup
                    count = cursor.count()
            except lmdb.BadValsizeError as ex:
                raise KeyError(f"Key: `{key}` is either empty, too big (for lmdb),"
                               " or wrong DUPFIXED size. ref) lmdb.BadValsizeError")
            return count


# used in IoDupSuber
    def getIoDupItemIter(self, db, key=b'', *, ion=0):
        """
        Iterates over branch of db given by key of IoDup items where each value
        has 33 byte insertion ordinal number proem (prefixed) with separator.
        Automagically removes (strips) proem before returning items.

        Assumes DB opened with dupsort=True

        Returns:
            ioitems (Iterator):  each item iterated is tuple (keys, ioval) where
                each keys is actual keys tuple and each ioval is dup that
                includes prefixed insertion ordering proem
                empty list if no entry at keys.
                Raises StopIteration when done


        Because cursor.iternext() advances cursor after returning item its safe
        to delete the item within the iteration loop. curson.iternext() works
        for both dupsort==False and dupsort==True

        Raises StopIteration Error when empty.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            key (bytes): truncated top key, a key space prefix to get all the items
                        from multiple branches of the key space. If top key is
                        empty then gets all items in database
            ion (int): starting ordinal value, default 0



        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if cursor.set_range(key):  # move to val at key >= key if any
                for ckey, cval in cursor.iternext():  # get key, val first dup at cursor
                    ckey = bytes(ckey)
                    if not ckey.startswith(key): #  prev entry if any last in branch
                        break  # done
                    cion = int(bytes(cval[:32]), 16)  # convert without sep '.' in [33]
                    if cion < ion:  # cion cursor insertion order proem as int
                        continue  # skip dups whose cion is below ion
                    yield (ckey, cval)  # include proem on val
            return  # done raises StopIteration


# used in IoDupSuber.getItemIter
    def getTopIoDupItemIter(self, db, top=b''):
        """
        Iterates over top branch of db given by key of IoDup items where each value
        has 33 byte insertion ordinal number proem (prefixed) with separator.
        Automagically removes (strips) proem before returning items.

        Assumes DB opened with dupsort=True

        Returns:
            items (abc.Iterator): iterator of (full key, val) tuples of all
            dup items  over a branch of the db given by top key where returned
            full key is full database key for val not truncated top key.
            Item is (key, val) with proem stripped from val stored in db.
            If key = b'' then returns list of dup items for all keys in db.


        Because cursor.iternext() advances cursor after returning item its safe
        to delete the item within the iteration loop. curson.iternext() works
        for both dupsort==False and dupsort==True

        Raises StopIteration Error when empty.

        Parameters:
            db (lmdb._Database): instance of named sub db with dupsort==False
            top (bytes): truncated top key, a key space prefix to get all the items
                        from multiple branches of the key space. If top key is
                        empty then gets all items in database

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).
        """
        for top, val in self.getTopItemIter(db=db, top=top):
            val = val[33:] # strip proem
            yield (top, val)

# not needed in IoDupSuber since not used anywhere always uses the Iter version
# below. confirm this in general and refactor any that do use to use the iter verio
    def getIoDupItemsNext(self, db, key=b"", skip=True):
        """
        Return list of all dup items at next key after key in db in insertion order.
        Item is (key, val) with proem stripped from val stored in db.
        If key == b'' then returns list of dup items at first key in db.
        If skip is False and key is not empty then returns dup items at key
        Returns empty list if no entries at next key after key

        If key is empty then gets io items (key, io value) at first key in db
        Use the return key from items as next key for next call to function in
        order to iterate through the database

        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace or empty string
            skip is Boolean If True skips to next key if key is not empty string
                    Othewise don't skip for first pass
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            items = []
            if cursor.set_range(key):  # moves to first_dup at key
                found = True
                if skip and key and cursor.key() == key:  # skip to next key
                    found = cursor.next_nodup()  # skip to next key not dup if any
                if found:
                    # slice off prepended ordering prefix on value in item
                    items = [(key, val[33:]) for key, val in cursor.iternext_dup(keys=True)]
            return items

# don't need this in IoDupSuber because can replace with self.getTopIoDupItemIter
# which in turen can be replaced with IoDupSuber.getItemIter

    def getIoDupItemsNextIter(self, db, key=b"", skip=True):
        """
        Return iterator of all dup items at next key after key in db in insertion order.
        Item is (key, val) with proem stripped from val stored in db.
        If key = b'' then returns list of dup items at first key in db.
        If skip is False and key is not empty then returns dup items at key
        Raises StopIteration Error when no remaining dup items = empty.

        If key is empty then gets io items (key, io value) at first key in db
        Use the return key from items as next key for next call to function in
        order to iterate through the database

        Assumes DB opened with dupsort=True

        Duplicates at a given key preserve insertion order of duplicate.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order.

        Duplicates are ordered as a pair of key plus value so prepending proem
        to each value changes duplicate ordering. Proem is 33 characters long.
        With 32 character hex string followed by '.' for essentiall unlimited
        number of values which will be limited by memory.

        With prepended proem ordinal must explicity check for duplicate values
        before insertion. Uses a python set for the duplicate inclusion test.
        Set inclusion scales with O(1) whereas list inclusion scales with O(n).

        Parameters:
            db is opened named sub db with dupsort=True
            key is bytes of key within sub db's keyspace or empty
            skip is Boolean If True skips to next key if key is not empty string
                    Othewise don't skip for first pass
        """

        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            if cursor.set_range(key):  # moves to first_dup at key
                found = True
                if skip and key and cursor.key() == key:  # skip to next key
                    found = cursor.next_nodup()  # skip to next key not dup if any
                if found:
                    for key, val in cursor.iternext_dup(keys=True):
                        yield (key, val[33:]) # slice off prepended ordering prefix

# Should not need this in OnIoDupSuber because can replace with get getIoDupItemIter

    def getIoDupValsAllPreIter(self, db, pre, on=0):
        """
        Returns iterator of all dup vals in insertion order for all entries
        with same prefix across all ordinal numbers in increasing order
        without gaps between ordinal numbers
        starting with on, default 0. Stops if gap or different pre.
        Assumes that key is combination of prefix and sequence number given
        by .snKey().
        Removes prepended proem ordinal from each val before returning

        Raises StopIteration Error when empty.

        Duplicates are retrieved in insertion order.

        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order
        Duplicates are ordered as a pair of key plus value so prepending prefix
        to each value changes duplicate ordering. Proem is 17 characters long.
        With 16 character hex string followed by '.'.

        Parameters:
            db is opened named sub db with dupsort=True
            pre (bytes | str): of itdentifier prefix prepended to sn in key
                within sub db's keyspace
            on (int): ordinal number to begin iteration at
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            key = snKey(pre, cnt:=on)
            while cursor.set_key(key):  # moves to first_dup
                for val in cursor.iternext_dup():
                    # slice off prepended ordering prefix
                    yield val[33:]
                key = snKey(pre, cnt:=cnt+1)


    def getIoDupValsAllPreBackIter(self, db, pre, on=0):
        """
        Returns iterator of all dup vals in insertion order for all entries
        with same prefix across all sequence numbers in decreasing order without gaps
        between ordinals at a given pre.
        Starting with on (default = 0) as begining ordinal number or sequence number.
        Stops if gap or different pre.
        Assumes that key is combination of prefix and sequence number given
        by .snKey().
        Removes prepended proem ordinal from each val before returning

        Raises StopIteration Error when empty.

        Duplicates are retrieved in insertion order.

        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order
        Duplicates are ordered as a pair of key plus value so prepending prefix
        to each value changes duplicate ordering. Proem is 17 characters long.
        With 16 character hex string followed by '.'.

        Parameters:
            db is opened named sub db with dupsort=True
            pre is bytes of identifier prefix prepended to sn in key
                within sub db's keyspace
            on (int): is ordinal number to begin iteration
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            key = snKey(pre, cnt := on)
            # set_key returns True if exact key else false
            while cursor.set_key(key):  # moves to first_dup if valid key
                for val in cursor.iternext_dup():
                    # slice off prepended ordering prefix
                    yield val[33:]
                key = snKey(pre, cnt:=cnt-1)


    def getIoDupValLastAllPreIter(self, db, pre, on=0):
        """
        Returns iterator of last only of dup vals of each key in insertion order
        for all entries with same prefix across all sequence numbers in increasing order
        without gaps starting with on (default = 0). Stops if gap or different pre.
        Assumes that key is combination of prefix and sequence number given
        by .snKey().
        Removes prepended proem ordinal from each val before returning

        Raises StopIteration Error when empty.

        Duplicates are retrieved in insertion order.

        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order
        Duplicates are ordered as a pair of key plus value so prepending prefix
        to each value changes duplicate ordering. Proem is 17 characters long.
        With 16 character hex string followed by '.'.


        Parameters:
            db is opened named sub db with dupsort=True
            pre is bytes of itdentifier prefix prepended to sn in key
                within sub db's keyspace
            on (int): ordinal number to being iteration
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            key = snKey(pre, cnt:=on)
            while cursor.set_key(key):  # moves to first_dup
                if cursor.last_dup(): # move to last_dup
                    yield cursor.value()[33:]  # slice off prepended ordering prefix
                key = snKey(pre, cnt:=cnt+1)

# used by .dels  getIoDupItemIter
    def getIoDupValsAnyPreIter(self, db, pre, on=0):
        """
        Returns iterator of all dup vals in insertion order for any entries
        with same prefix across all ordinal numbers in order including gaps
        between ordinals at a given pre. Staring with on (default = 0).
        Stops when pre is different.

        Duplicates that may be deleted such as duplicitous event logs need
        to be able to iterate across gaps in ordinal number.

        Assumes that key is combination of prefix and sequence number given
        by .snKey().
        Removes prepended proem ordinal from each val before returning

        Raises StopIteration Error when empty.

        Duplicates are retrieved in insertion order.
        Because lmdb is lexocographic an insertion ordering proem is prepended to
        all values that makes lexocographic order that same as insertion order
        Duplicates are ordered as a pair of key plus value so prepending prefix
        to each value changes duplicate ordering. Proem is 17 characters long.
        With 16 character hex string followed by '.'.

        Parameters:
            db is opened named sub db with dupsort=True
            pre is bytes of itdentifier prefix prepended to sn in key
                within sub db's keyspace
            on (int): beginning ordinal number to start iteration
        """
        with self.env.begin(db=db, write=False, buffers=True) as txn:
            cursor = txn.cursor()
            key = snKey(pre, cnt:=on)
            while cursor.set_range(key):  #  moves to first dup of key >= key
                key = cursor.key()  # actual key
                front, back = bytes(key).split(sep=b'.', maxsplit=1)
                if front != pre:  # set range may skip pre if none
                    break
                for val in cursor.iternext_dup():
                    yield val[33:]  # slice off prepended ordering prefix
                cnt = int(back, 16)
                key = snKey(pre, cnt:=cnt+1)


    # methods for OnIoDup that combines IoDup value proem with On ordinal numbered
    # trailing prefix
    # this is so we do the proem add and strip here not in some higher level class
    # like suber

    # used in OnIoDupSuber
    def appendOnIoDupVal(self, db, key, val, *, sep=b'.'):
        """
        Appends val in order after last previous key with same pre in db where
        full key has key prefix and serialized on suffix attached with sep and
        value has ordinal proem prefixed.
        Returns ordinal number in, on, of appended entry. Appended on is 1 greater
        than previous latest on at pre.
        Uses onKey(pre, on) for entries.

        Works with either dupsort==True or False since always creates new full
        key.

        Append val to end of db entries with same pre but with on incremented by
        1 relative to last preexisting entry at pre.

        Returns:
            on (int): ordinal number of newly appended val

        Parameters:
            db (subdb): named sub db in lmdb
            key (bytes): key within sub db's keyspace plus trailing part on
            val (bytes): serialized value to append
            sep (bytes): separator character for split
        """
        val = (b'%032x.' % (0)) +  val  # prepend ordering proem
        return (self.appendOnVal(db=db, key=key, val=val, sep=sep))

    # used in OnIoDupSuber
    def getOnIoDupItemIter(self, db, key=b'', on=0, *, sep=b'.'):
        """
        Returns iterator of triples (key, on, val), at each key over all ordinal
        numbered keys with same key + sep + on in db. Values are sorted by
        onKey(key, on) where on is ordinal number int and key is prefix sans on.
        Values duplicates are sorted internally by hidden prefixed insertion order
        proem ordinal
        Returned items are triples of (key, on, val)
        When dupsort==true then duplicates are included in items since .iternext
        includes duplicates.
        when key is empty then retrieves whole db

        Raises StopIteration Error when empty.

        Returns:
            items (Iterator[(key, on, val)]): triples of key, on, val

        Parameters:
            db (subdb): named sub db in lmdb
            key (bytes): key within sub db's keyspace plus trailing part on
                when key is empty then retrieves whole db
            on (int): ordinal number at which to initiate retrieval
            sep (bytes): separator character for split
        """
        for key, on, val in self.getOnItemIter(db=db, key=key, on=on, sep=sep):
            val = val[33:] # strip proem
            yield (key, on, val)
