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


def test_resolution_remote_ref_is_not_fetched():
    """ A $ref naming a remote URL must resolve only against the local
    cache and fail closed when it misses, never be fetched over the
    network.

    Schemas arrive from other parties, so fetching a URL one names would
    let a received credential drive outbound requests from the node
    validating it, and make validation depend on a remote host. The
    deprecated RefResolver did exactly that -- it fetched http(s) refs
    through requests -- which is one reason this resolves through a
    referencing Registry whose only source is .db.schema.
    """
    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "allOf": [
            {"$ref": "https://example.invalid/evil.json"},
            {"type": "object"},
        ],
    }
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="remote-ref-not-fetched") as db:
        cache = CacheResolver(db=db)

        # anything reaching the network would raise something other than a
        # clean ValidationError here, and would be slow doing it
        requested = []
        realHandler = cache.handler

        def trackingHandler(uri):
            requested.append(uri)
            return realHandler(uri)

        cache.handler = trackingHandler

        schemer = Schemer(raw=raw, resolver=cache)

        with pytest.raises(ValidationError):
            schemer.verify(b'{}')

        # the ref was offered to the local cache, and only to it
        assert requested == ["https://example.invalid/evil.json"]


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


def test_cache_resolver_retrieval_is_lazy():
    """ Resolution must read only the schemas a $ref actually names, not
    the whole local schema cache. Reading all of db.schema on every
    credential check would cost a read and a JSON parse per cached
    schema, growing with however many schemas the Habery has ever seen.
    """
    sads = []
    for field in ("z", "y", "x"):
        sad = {
            "$id": "",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "required": [field],
            "properties": {field: {"type": "number"}},
        }
        saider, sad = Saider.saidify(sad, label=Saids.dollar)
        sads.append((saider.qb64, dumps(sad)))

    refsaid, ref = sads[0]

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
    sad["allOf"][0]["$ref"] = refsaid
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="cache-resolver-lazy") as db:
        cache = CacheResolver(db=db)
        for said, schema in sads:  # three cached, only one of them referenced
            cache.add(said, schema)

        gets = []
        realGet = db.schema.get

        def countedGet(keys, *pa, **kwa):
            gets.append(keys)
            return realGet(keys, *pa, **kwa)

        db.schema.get = countedGet

        schemer = Schemer(raw=raw, resolver=cache)
        assert schemer.verify(b'{"a": "x", "z": 1}') is True

        # only the referenced schema was read, not the other two
        assert gets == [refsaid]


def test_cache_resolver_registry_picks_up_later_additions():
    """ CacheResolver builds one registry and reuses it, so a schema added
    after that registry exists -- including after a check already failed
    on it being missing -- must still resolve, with no cache to
    invalidate by hand.
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

    with basing.openDB(name="cache-resolver-later-additions") as db:
        cache = CacheResolver(db=db)
        schemer = Schemer(raw=raw, resolver=cache)

        # miss: refsaid not cached yet, so this must fail closed
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": "x", "z": 1}')

        cache.add(refsaid, ref)

        # hit: the same resolver, and the same registry, now resolves it
        assert schemer.verify(b'{"a": "x", "z": 1}') is True

        # and the newly resolvable schema is enforced, not just reachable
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": "x"}')


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


def test_resolution_internal_fragment_ref():
    """ A $ref internal to the schema being validated (e.g.
    "#/definitions/...") must resolve whether or not a resolver is
    attached and whether or not the schema itself is in db.schema.

    The validator pushes the schema's $id as the resolution scope, so a
    "#/..." ref is joined onto that $id and looked up as
    "<said>#/definitions/...". That only works if the schema is
    registered in the resolver under its own $id, which is why
    CacheResolver.resolver() is given the schema as its referrer.
    Previously it was given the instance being validated instead, and
    this failed with "unknown url type: 'E...'".
    """
    sad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "definitions": {"s": {"type": "string"}},
        "required": ["a"],
        "properties": {"a": {"$ref": "#/definitions/s"}},
    }
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    said = saider.qb64
    raw = dumps(sad)

    with basing.openDB(name="internal-fragment-ref") as db:
        # baseline: no resolver at all
        assert Schemer(raw=raw).verify(b'{"a": "x"}') is True

        cache = CacheResolver(db=db)

        # schema is not in db.schema -- only ever handed in as raw
        schemer = Schemer(raw=raw, resolver=cache)
        assert schemer.verify(b'{"a": "x"}') is True

        # the internal ref must still actually constrain, not be skipped
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": 1}')

        with pytest.raises(ValidationError):
            schemer.verify(b'{}')

        # and once the schema is in db.schema too, where it is reachable
        # through .store as well as through the referrer
        cache.add(said, raw)
        cached = Schemer(raw=raw, resolver=cache)
        assert cached.verify(b'{"a": "x"}') is True

        with pytest.raises(ValidationError):
            cached.verify(b'{"a": 1}')


def test_resolution_internal_fragment_and_said_ref():
    """ A schema may use both styles of $ref at once: a bare SAID into
    another cached schema, and an internal fragment into its own
    definitions. Both must resolve in the same schema.

    This combination was broken under jsonschema's deprecated
    RefResolver: Validator.__attrs_post_init__ calls
    push_scope(id_of(schema)) with no matching pop_scope (its own comment
    reads "REMOVEME: Legacy ref resolution state management"), so
    descending into a $ref whose target carries its own $id leaked that
    $id onto the scope stack permanently and every later relative ref in
    the schema was joined onto the wrong base. Every schema cached by
    KERI carries $id = its own SAID, so any bare-SAID $ref tripped it.
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
        "definitions": {"s": {"type": "string"}},
        "allOf": [
            {"$ref": ""},
            {
                "type": "object",
                "required": ["a"],
                "properties": {"a": {"$ref": "#/definitions/s"}},
            },
        ],
    }
    sad["allOf"][0]["$ref"] = refsaid
    saider, sad = Saider.saidify(sad, label=Saids.dollar)
    raw = dumps(sad)

    with basing.openDB(name="internal-and-said-ref") as db:
        cache = CacheResolver(db=db)
        cache.add(refsaid, ref)  # only the referenced schema is cached

        schemer = Schemer(raw=raw, resolver=cache)

        assert schemer.verify(b'{"a": "x", "z": 1}') is True

        # the internal fragment ref still constrains
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": 1, "z": 1}')

        # the bare-SAID ref still constrains
        with pytest.raises(ValidationError):
            schemer.verify(b'{"a": "x"}')


if __name__ == '__main__':
    test_json_schema()
    test_json_schema_dict()
    test_resolution()
