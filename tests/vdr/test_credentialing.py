# -*- encoding: utf-8 -*-
"""
tests.vdr.credentialing module

"""
from keri import kering
from keri.app import habbing
from keri.core import coring, scheming
from keri.vc import proving
from keri.vdr import credentialing, verifying


def _pinChainedSchema(db):
    """ Pin a base schema and a derived schema into db.schema, where the
    derived schema's top-level allOf[0].$ref is the base schema's bare SAID
    (no "did:" scheme prefix). The base schema requires an attribute ("z")
    that only the base contributes, and the derived schema separately
    requires its own attribute ("m"), so tests can independently prove
    each half of the chain is enforced.

    Returns:
        tuple(str, str): (base schema SAID, derived schema SAID)
    """
    basesad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Base",
        "type": "object",
        "required": ["v", "d", "i", "s", "a"],
        "properties": {
            "v": {"type": "string"},
            "d": {"type": "string"},
            "i": {"type": "string"},
            "s": {"type": "string"},
            "a": {
                "type": "object",
                "additionalProperties": True,
                "required": ["d", "z"],
                "properties": {
                    "d": {"type": "string"},
                    "z": {"type": "string"},
                },
            },
        },
    }
    _, basesad = coring.Saider.saidify(basesad, label=coring.Saids.dollar)
    baseschemer = scheming.Schemer(sed=basesad)
    db.schema.pin(keys=(baseschemer.said,), val=baseschemer)

    derivedsad = {
        "$id": "",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "Derived",
        "allOf": [
            {"$ref": ""},
            {
                "type": "object",
                "additionalProperties": True,
                "required": ["ri"],
                "properties": {
                    "ri": {"type": "string"},
                    "a": {
                        "type": "object",
                        "additionalProperties": True,
                        "required": ["m"],
                        "properties": {"m": {"type": "string"}},
                    },
                },
            },
        ],
    }
    derivedsad["allOf"][0]["$ref"] = baseschemer.said
    _, derivedsad = coring.Saider.saidify(derivedsad, label=coring.Saids.dollar)
    derivedschemer = scheming.Schemer(sed=derivedsad)
    db.schema.pin(keys=(derivedschemer.said,), val=derivedschemer)

    return baseschemer.said, derivedschemer.said


def test_credentialer_create_chained_schema():
    """ Credentialer.create() -> validate() must succeed for a credential
    issued against a schema that inherits from a base schema via a
    bare-SAID $ref, and must still enforce requirements contributed by
    *either* half of the chain independently.
    """
    with habbing.openHab(name="issuer", temp=True, salt=b'0123456789abcdef') as (hby, hab):
        basesaid, derivedsaid = _pinChainedSchema(hby.db)

        regery = credentialing.Regery(hby=hby, name="issuer", temp=True)
        registry = regery.makeRegistry(prefix=hab.pre, name="test")

        verifier = verifying.Verifier(hby=hby, reger=regery.reger)
        credentialer = credentialing.Credentialer(hby=hby, rgy=regery, registrar=None, verifier=verifier)

        # satisfies both the base-contributed requirement (a.z) and the
        # derived-only requirement (a.m)
        creder = credentialer.create(regname="test", recp=None, schema=derivedsaid,
                                     source=None, rules=None, data={"z": "zval", "m": "mval"})
        assert creder.sad["s"] == derivedsaid
        assert creder.sad["a"]["z"] == "zval"
        assert creder.sad["a"]["m"] == "mval"

        # sanity: the base schema alone is still resolvable/usable on its own
        assert hby.db.schema.get(keys=(basesaid,)) is not None


def test_credentialer_create_chained_schema_missing_base_required_field():
    """ A credential that satisfies the derived schema's own requirements
    but omits a field required only by the inherited base schema must still
    be rejected -- proves the fix doesn't just make $ref "always pass", it
    actually resolves and enforces the base schema's constraints.
    """
    with habbing.openHab(name="issuer", temp=True, salt=b'0123456789abcdef') as (hby, hab):
        _, derivedsaid = _pinChainedSchema(hby.db)

        regery = credentialing.Regery(hby=hby, name="issuer", temp=True)
        regery.makeRegistry(prefix=hab.pre, name="test")

        verifier = verifying.Verifier(hby=hby, reger=regery.reger)
        credentialer = credentialing.Credentialer(hby=hby, rgy=regery, registrar=None, verifier=verifier)

        try:
            credentialer.create(regname="test", recp=None, schema=derivedsaid,
                                source=None, rules=None, data={"m": "mval"})  # missing base-required 'z'
            assert False, "expected ConfigurationError for missing base-required field"
        except kering.ConfigurationError as ex:
            assert "Credential schema validation failed" in str(ex)


def test_credentialer_create_chained_schema_missing_derived_required_field():
    """ A credential that satisfies the inherited base schema but omits a
    field required only by the derived schema's own (non-$ref) allOf branch
    must still be rejected -- proves the derived branch isn't short-circuited
    once the $ref branch resolves.
    """
    with habbing.openHab(name="issuer", temp=True, salt=b'0123456789abcdef') as (hby, hab):
        _, derivedsaid = _pinChainedSchema(hby.db)

        regery = credentialing.Regery(hby=hby, name="issuer", temp=True)
        regery.makeRegistry(prefix=hab.pre, name="test")

        verifier = verifying.Verifier(hby=hby, reger=regery.reger)
        credentialer = credentialing.Credentialer(hby=hby, rgy=regery, registrar=None, verifier=verifier)

        try:
            credentialer.create(regname="test", recp=None, schema=derivedsaid,
                                source=None, rules=None, data={"z": "zval"})  # missing derived-required 'm'
            assert False, "expected ConfigurationError for missing derived-required field"
        except kering.ConfigurationError as ex:
            assert "Credential schema validation failed" in str(ex)


def test_credentialer_create_unresolvable_ref_schema():
    """ If the base schema a derived schema $refs was never cached locally,
    issuance must still fail closed with a clear error, not silently
    succeed or crash uncontrolled.
    """
    with habbing.openHab(name="issuer", temp=True, salt=b'0123456789abcdef') as (hby, hab):
        derivedsad = {
            "$id": "",
            "$schema": "http://json-schema.org/draft-07/schema#",
            "allOf": [
                {"$ref": "EDoesNotExistInLocalCache00000000000000000"},
                {"type": "object", "required": ["v", "d", "i", "s", "ri"]},
            ],
        }
        _, derivedsad = coring.Saider.saidify(derivedsad, label=coring.Saids.dollar)
        derivedschemer = scheming.Schemer(sed=derivedsad)
        hby.db.schema.pin(keys=(derivedschemer.said,), val=derivedschemer)

        regery = credentialing.Regery(hby=hby, name="issuer", temp=True)
        regery.makeRegistry(prefix=hab.pre, name="test")

        verifier = verifying.Verifier(hby=hby, reger=regery.reger)
        credentialer = credentialing.Credentialer(hby=hby, rgy=regery, registrar=None, verifier=verifier)

        try:
            credentialer.create(regname="test", recp=None, schema=derivedschemer.said,
                                source=None, rules=None, data={})
            assert False, "expected ConfigurationError for unresolvable $ref"
        except kering.ConfigurationError as ex:
            assert "Credential schema validation failed" in str(ex)
