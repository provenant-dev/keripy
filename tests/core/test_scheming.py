# -*- encoding: utf-8 -*-
"""
tests keri.core.scheming

"""
import json

import pytest

from keri.core.coring import MtrDex, dumps, Saider, Saids
from keri.core.scheming import Schemer, JSONSchema, CacheResolver
from keri.db import basing
from keri.kering import ValidationError


def test_json_schema():
    """ Tests to validate JSON schema with SAIDS"""
    # unsaidified sad of schema
    ssad = \
    {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties":
        {
            "a":
            {
                "type": "string"
            },
            "b":
            {
                "type": "number"
            },
            "c":
            {
                "type": "string",
                "format": "date-time"
            }
        }
    }

    # generate serialized saidified schema ssad
    saider, ssad = Saider.saidify(ssad, label=Saids.dollar)
    assert saider.qb64 == 'EMRvS7lGxc1eDleXBkvSHkFs8vUrslRcla6UXOJdcczw'
    sser = dumps(ssad)
    assert sser == (b'{"$id":"EMRvS7lGxc1eDleXBkvSHkFs8vUrslRcla6UXOJdcczw","$schema":"http://json'
        b'-schema.org/draft-07/schema#","type":"object","properties":{"a":{"type":"str'
        b'ing"},"b":{"type":"number"},"c":{"type":"string","format":"date-time"}}}')


    payload = b'{"a": "test", "b": 123, "c": "2018-11-13T20:20:39+00:00"}'
    mismatch = b'{"a": "test", "b": "123", "c": "2018-11-13T20:20:39+00:00"}'
    badjson = b'{"a": "test" "b": 123 "c": "2018-11-13T20:20:39+00:00"}'

    sce = Schemer(raw=sser)
    assert sce.said == saider.qb64
    assert sce.verify(raw=payload) is True
    with pytest.raises(ValidationError):
        sce.verify(raw=mismatch)

    with pytest.raises(ValidationError):
        sce.verify(raw=badjson)

    payload = b'{"a": "test", "c": "2018-11-13T20:20:39+00:00"}'
    assert sce.verify(raw=payload) is True

    payload = b'{"a": "test", "b": 123, "c": "2018-11-13T20:20:39+00:00", d:"not valid"}'
    with pytest.raises(ValidationError):
        sce.verify(raw=payload)

    # Invalid SAID for given schema
    badsaid = (b'{"$id": "EAG9LuUbFzV4OV5cGS9IeQWzy9SuyVFyVrpRc4l1xzPz", "$schema": '
               b'"http://json-schema.org/draft-07/schema#", "type": "object", "properties": {"a": {"type": "string"}, '
               b'"b": {"type": "number"}, "c": {"type": "string", "format": "date-time"}}}')

    with pytest.raises(ValidationError):
        Schemer(raw=badsaid)

    # Invalid schema  with invalid type "foo" not object
    invalid = (b'{"$id": "EOo3qzfwxPxY5VvhM816apl1zEV88F1CICr_BSKy45lk", "$schema": '
               b'"http://json-schema.org/draft-07/schema#", "type": "foo", "properties": {"a": {"type": "string"}, '
               b'"b": {"type": "number"}, "c": {"type": "string", "format": "date-time"}}}')

    with pytest.raises(ValidationError):
        Schemer(raw=invalid)


def test_json_schema_dict():
    sed = dict()
    sed["$id"] = ""
    sed["$schema"] = "http://json-schema.org/draft-07/schema#"
    sed.update(dict(
        type="object",
        properties=dict(
            a=dict(
                type="string"
            ),
            b=dict(
                type="number"
            ),
            c=dict(
                type="string",
                format="date-time"
            )
        )
    ))

    payload = b'{"a": "test", "b": 123, "c": "2018-11-13T20:20:39+00:00"}'
    mismatch = b'{"a": "test", "b": "123", "c": "2018-11-13T20:20:39+00:00"}'
    badjson = b'{"a": "test" "b": 123 "c": "2018-11-13T20:20:39+00:00"}'

    sce = Schemer(sed=sed, typ=JSONSchema(), code=MtrDex.Blake3_256)
    said = 'EMRvS7lGxc1eDleXBkvSHkFs8vUrslRcla6UXOJdcczw'
    assert sce.said == sce.sed["$id"] == said
    assert sce.verify(raw=payload) is True
    with pytest.raises(ValidationError):
        sce.verify(raw=mismatch)

    with pytest.raises(ValidationError):
        sce.verify(raw=badjson)

    raw = json.dumps(sce.sed).encode("utf-8")

    sce = Schemer(raw=raw)
    assert sce.said ==said

    # Invalid JSON Schema
    sed = dict()
    sed["$id"] = ""
    sed["$schema"] = "http://json-schema.org/draft-07/schema#"
    sed.update(dict(
        type="foo",
        properties=dict(
            a=dict(
                type="string"
            ),
            b=dict(
                type="number"
            ),
            c=dict(
                type="string",
                format="date-time"
            )
        )
    ))

    with pytest.raises(ValidationError):
        Schemer(sed=sed, code=MtrDex.Blake3_256)

    # Nested JSON Schema
    sed = dict()
    sed["$id"] = ""
    sed["$schema"] = "http://json-schema.org/draft-07/schema#"
    sed.update(dict(
        type="object",
        properties=dict(
            a=dict(
                type="object",
                properties=dict(
                    b=dict(
                        type="number"
                    ),
                    c=dict(
                        type="string",
                        format="date-time"
                    )
                )
            ),
        )
    ))

    sce = Schemer(sed=sed, code=MtrDex.Blake3_256)
    said = 'ENQKl3r1Z6HiLXOD-050aVvKziCWJtXWg3vY2FWUGSxG'
    assert sce.said == said

    payload = b'{"a": {"b": 123, "c": "2018-11-13T20:20:39+00:00"}}'
    assert sce.verify(payload)

    # Additional hash types
    sce = Schemer(sed=sed, code=MtrDex.Blake2b_256)
    assert sce.said == 'FH9xV58dp3KsCMMKUm2OH6M3S9NTkCt3fUxtRI6fQ2Tf'
    sce = Schemer(sed=sed, code=MtrDex.Blake2s_256)
    assert sce.said == 'GEYnRCwpnZPuO7NDiOhAFZNTwaJb0tR3rc1W8W8ATSGy'
    sce = Schemer(sed=sed, code=MtrDex.SHA3_256)
    assert sce.said == 'HJg5rPYDdG9GY5rux8k9hxA5HZ2jmJvtSoMSCITU0D2i'
    sce = Schemer(sed=sed, code=MtrDex.SHA2_256)
    assert sce.said == 'IL09buY7cHFUJehpThsnzXqMiaEpil5zsCciGbgdlbIe'
    sce = Schemer(sed=sed, code=MtrDex.Blake3_512)
    assert sce.said == '0DB0Fp_mZA2QmS7VIysDR87HUHY_Dhrxmt463x9SnaoCMNKpN-ObJRxfY3C3bzBZsPUTzTgAIaTLz6qea2spJTTm'
    sce = Schemer(sed=sed, code=MtrDex.Blake2b_512)
    assert sce.said == '0EDWHpoDWLjzJfWc08RVvFTCjzZ7oPBgi7ml_q3LrHJu4qnMtjD4dCsHF-XTauGl8FyLfX09e3gEv_WAGqxzpDqD'
    sce = Schemer(sed=sed, code=MtrDex.SHA3_512)
    assert sce.said == '0FABhaP0YVHGH5iumlxHmWlUzWub6x7PUroMNMoZ9OWN9tg9x2l5q0GXjobwhexBQbzDDQBuoNlHN4W5ZZqvbADI'
    sce = Schemer(sed=sed, code=MtrDex.SHA2_512)
    assert sce.said == '0GCQq-oxku9J-waFh-XzBNkCrsa_iSECzy_smZQ0HNn5Y64vbVGQmnFqJNcyTj9LzD_LvcCd-NBkrTpWvQoxh3HD'


def test_resolution():
    """ Test resolve in db schema SAID references in another schema """
    refsad = \
    {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties":
        {
            "z":
            {
                "type": "number"
            }
        }
    }

    # generate serialized saidified schema refsad
    saider, refsad = Saider.saidify(refsad, label=Saids.dollar)
    refsaid = saider.qb64
    assert refsaid == 'EL3Luusa97P8dZOCI8KEN2ShG35HVS8S6-z1vuu52F-C'
    ref = dumps(refsad)

    ssad = \
    {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties":
        {
            "a":
            {
                "type": "string"
            },
            "b":
            {
                "type": "number"
            },
            "c":
            {
                "type": "string",
                "format": "date-time"
            },
            "xy":
            {
                "$ref": ""
            }
        }
    }

    ssad["properties"]["xy"]["$ref"] = f"did:keri:{refsaid}"

    # generate serialized saidified schema ssad
    saider, ssad = Saider.saidify(ssad, label=Saids.dollar)
    said = saider.qb64
    assert said == 'EKcRFuOiLUMEgTljL8FWPOpDosH2Cz38HhgdmRKpUHTe'
    sser = dumps(ssad)
    assert sser ==  (b'{"$id":"EKcRFuOiLUMEgTljL8FWPOpDosH2Cz38HhgdmRKpUHTe","$schema":"http://json'
                    b'-schema.org/draft-07/schema#","type":"object","properties":{"a":{"type":"str'
                    b'ing"},"b":{"type":"number"},"c":{"type":"string","format":"date-time"},"xy":'
                    b'{"$ref":"did:keri:EL3Luusa97P8dZOCI8KEN2ShG35HVS8S6-z1vuu52F-C"}}}')


    scer = (
        b'{'
        b'   "$id": "EDfHSaA1XvjltvoO1flnZVuNr8y-wWvGTBKiP1naFxUs", '
        b'   "$schema": "http://json-schema.org/draft-07/schema#", '
        b'   "type": "object", '
        b'   "properties": {'
        b'      "a": {'
        b'         "type": "string"'
        b'      }, '
        b'      "b": {'
        b'         "type": "number"'
        b'      }, '
        b'      "c": {'
        b'         "type": "string", '
        b'         "format": "date-time"'
        b'      },'
        b'      "xy": {'
        b'         "$ref": "did:keri:Evcu66xr3s_x1k4IjwoQ3ZKEbfkdVLxLr7PW-67nYX4I"'
        b'      }'
        b'   }'
        b'}')

    payload = b'{"a": "test", "b": 123, "c": "2018-11-13T20:20:39+00:00", "xy": {"z": 456}}'
    badload = b'{"a": "test", "b": 123, "c": "2018-11-13T20:20:39+00:00", "xy": {"z": "456"}}'

    with basing.openDB(name="edy") as db:
        cache = CacheResolver(db=db)
        cache.add(refsaid, ref)  # add referenced schema to db indexed by its said

        schemer = Schemer(raw=sser)
        schemer.typ = JSONSchema(resolver=cache)
        v = schemer.verify(payload)
        assert v is True

        with pytest.raises(ValidationError):
            schemer.verify(badload)


def test_resolution_bare_said_ref():
    """ Test resolving a bare-SAID $ref (no "did:" scheme prefix) via
    CacheResolver, including a two-level chain to confirm transitive
    resolution and that a field required only by the middle schema in the
    chain is still enforced.
    """
    basesad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["z"],
        "properties": {"z": {"type": "number"}},
    }
    saider, basesad = Saider.saidify(basesad, label=Saids.dollar)
    basesaid = saider.qb64
    base = dumps(basesad)

    midsad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": ""},
            {
                "type": "object",
                "required": ["m"],
                "properties": {"m": {"type": "string"}},
            },
        ],
    }
    midsad["allOf"][0]["$ref"] = basesaid
    saider, midsad = Saider.saidify(midsad, label=Saids.dollar)
    midsaid = saider.qb64
    mid = dumps(midsad)

    topsad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": ""},
            {
                "type": "object",
                "required": ["t"],
                "properties": {"t": {"type": "string"}},
            },
        ],
    }
    topsad["allOf"][0]["$ref"] = midsaid
    saider, topsad = Saider.saidify(topsad, label=Saids.dollar)
    top = dumps(topsad)

    good = json.dumps({"z": 1, "m": "x", "t": "y"}).encode("utf-8")
    missingMid = json.dumps({"z": 1, "t": "y"}).encode("utf-8")
    missingBase = json.dumps({"m": "x", "t": "y"}).encode("utf-8")
    missingTop = json.dumps({"z": 1, "m": "x"}).encode("utf-8")

    with basing.openDB(name="bare-said-ref") as db:
        cache = CacheResolver(db=db)
        cache.add(basesaid, base)  # only base and mid are pre-cached; top is the schema under test
        cache.add(midsaid, mid)

        schemer = Schemer(raw=top)
        schemer.typ = JSONSchema(resolver=cache)

        assert schemer.verify(good) is True

        # each level's required field must still be independently enforced
        # through the chain, not short-circuited by the other levels passing
        with pytest.raises(ValidationError):
            schemer.verify(missingMid)

        with pytest.raises(ValidationError):
            schemer.verify(missingBase)

        with pytest.raises(ValidationError):
            schemer.verify(missingTop)


def test_resolution_unresolvable_bare_said_ref():
    """ A bare-SAID $ref to a schema that was never cached locally must still
    fail closed, not be silently treated as satisfied.
    """
    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": "EDoesNotExistInLocalCache00000000000000000"},
            {"type": "object"},
        ],
    }
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="unresolvable-said-ref") as db:
        cache = CacheResolver(db=db)  # nothing added to the cache

        schemer = Schemer(raw=raw)
        schemer.typ = JSONSchema(resolver=cache)

        with pytest.raises(ValidationError):
            schemer.verify(b'{}')


def test_resolution_no_ref_with_resolver_present():
    """ A plain schema with no $ref at all must still validate normally when
    a resolver is attached, i.e. attaching a resolver must not change
    behavior for schemas that don't use it.
    """
    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["a"],
        "properties": {"a": {"type": "string"}},
    }
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="no-ref-with-resolver") as db:
        cache = CacheResolver(db=db)

        schemer = Schemer(raw=raw)
        schemer.typ = JSONSchema(resolver=cache)

        assert schemer.verify(b'{"a": "x"}') is True

        with pytest.raises(ValidationError):
            schemer.verify(b'{}')


def test_cache_resolver_resolver_store_is_cached():
    """ CacheResolver.resolver() rebuilds its jsonschema store from every
    schema in db.schema, which would mean re-reading and re-parsing that
    entire local cache on every single credential check if done on every
    call. It should instead reuse the store across calls as long as
    db.schema hasn't changed, and only rebuild once a new schema is added.
    """
    basesad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["z"],
        "properties": {"z": {"type": "number"}},
    }
    saider, basesad = Saider.saidify(basesad, label=Saids.dollar)
    basesaid = saider.qb64
    base = dumps(basesad)

    with basing.openDB(name="cache-resolver-store-caching") as db:
        cache = CacheResolver(db=db)

        calls = []
        realGetItemIter = db.schema.getItemIter

        def countedGetItemIter(*pa, **kwa):
            calls.append(1)
            return realGetItemIter(*pa, **kwa)

        db.schema.getItemIter = countedGetItemIter

        cache.resolver()
        cache.resolver()
        cache.resolver()
        assert len(calls) == 1  # nothing changed in db.schema; store built once, then reused

        cache.add(basesaid, base)

        r = cache.resolver()
        assert basesaid in r.store  # new schema is picked up
        assert len(calls) == 2  # db.schema changed; store was rebuilt exactly once more

        cache.resolver()
        assert len(calls) == 2  # unchanged again since the rebuild; still reused


def test_cache_resolver_store_not_mutated_by_resolution():
    """ CacheResolver._store is reused across .resolver() calls, so nothing
    resolving against it, a hit or a miss, on any $ref style, may leave
    it changed afterward. jsonschema.RefResolver copies the store it's
    given at construction time rather than holding a reference to it, so
    this holds today; this test exists to catch it directly if that ever
    stops being true.
    """
    refsad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["z"],
        "properties": {"z": {"type": "number"}},
    }
    saider, refsad = Saider.saidify(refsad, label=Saids.dollar)
    refsaid = saider.qb64
    ref = dumps(refsad)

    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": ""},
            {
                "type": "object",
                "required": ["a"],
                "properties": {"a": {"type": "string"}},
            },
        ],
    }
    sad["allOf"][0]["$ref"] = f"did:keri:{refsaid}"
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="cache-resolver-store-not-mutated") as db:
        cache = CacheResolver(db=db)
        schemer = Schemer(raw=raw)
        schemer.typ = JSONSchema(resolver=cache)

        # miss: refsaid not cached yet -- CacheResolver._store must stay
        # untouched by the failed lookup
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": "x", "z": 1}')
        assert cache._store == {}

        cache.add(refsaid, ref)

        # hit: refsaid now resolves -- CacheResolver._store must contain
        # only what it built from db.schema, not anything jsonschema's own
        # did: resolution added on top of that
        assert schemer.verify(b'{"a": "x", "z": 1}') is True
        assert set(cache._store.keys()) == {refsaid}


def test_cache_resolver_missing_ref_fails_the_same_way_on_repeated_calls():
    """ Two failed lookups for the same unresolvable $ref, with nothing
    added to db.schema in between, must fail the same clean way both
    times -- not succeed incorrectly, and not fail differently or worse
    the second time around because the store was reused instead of
    rebuilt from scratch.
    """
    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": "did:keri:EDoesNotExistInLocalCache00000000000000000"},
            {"type": "object"},
        ],
    }
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="cache-resolver-repeated-miss") as db:
        cache = CacheResolver(db=db)
        schemer = Schemer(raw=raw)
        schemer.typ = JSONSchema(resolver=cache)

        first = None
        second = None
        try:
            schemer.verify(b'{}')
        except ValidationError as ex:
            first = str(ex)

        try:
            schemer.verify(b'{}')
        except ValidationError as ex:
            second = str(ex)

        assert first is not None
        assert first == second


if __name__ == '__main__':
    test_json_schema()
    test_json_schema_dict()
    test_resolution()
