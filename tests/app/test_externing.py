# -*- encoding: utf-8 -*-
"""
tests.app.test_externing module

Tests for the ExternModule plug-in point (Algos.extern) that lets a Manager /
Habery delegate key creation and signing to an external key store (HSM etc).
"""
import pytest

from keri import kering
from keri.app import habbing, keeping
from keri.app.keeping import Algos, ExternModule
from keri.core import coring, signing


class FakeExtern(ExternModule):
    """In-memory ExternModule: holds Ed25519 seeds keyed by an opaque handle.

    Records every call so tests can assert exactly what the Manager passed in.
    """

    def __init__(self):
        self.signers = {}      # handle -> (current signer, next signer)
        self.calls = []

    def incept(self, stem=None, transferable=True, ncount=1, dcode=coring.MtrDex.Blake3_256, **kwa):
        self.calls.append(("incept", stem, transferable, kwa))
        code = coring.MtrDex.Ed25519_Seed
        cur = signing.Signer(code=code, transferable=transferable)
        nxt = signing.Signer(code=code, transferable=transferable)
        self.signers[stem] = (cur, nxt)
        verfers = [cur.verfer]
        digers = [coring.Diger(ser=nxt.verfer.qb64b, code=dcode)] if transferable else []
        return verfers, digers

    def sign(self, ser, pre=None, stem=None, verfers=None, pubs=None,
             indexed=True, indices=None, ondices=None, **kwa):
        self.calls.append(("sign", pre, stem))
        signer = self.signers[stem][0]
        i = indices[0] if indices else 0
        if indexed:
            return [signer.sign(ser, index=i)]
        return [signer.sign(ser)]


def test_base_class_methods_raise_not_implemented():
    mod = ExternModule()
    with pytest.raises(NotImplementedError):
        mod.incept()
    with pytest.raises(NotImplementedError):
        mod.rotate(pre="EExample")
    with pytest.raises(NotImplementedError):
        mod.sign(ser=b"test")


def test_exported_from_keeping():
    from keri.app import externing
    assert keeping.ExternModule is externing.ExternModule


def test_manager_extern_without_module_raises():
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks)
        assert mgr.extern is None
        with pytest.raises(ValueError, match="no extern"):
            mgr.incept(algo=Algos.extern, stem="h1", temp=True)


def test_manager_extern_incept_stores_params_and_pubs():
    ext = FakeExtern()
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext)
        verfers, digers = mgr.incept(algo=Algos.extern, stem="h1", temp=True)

        assert len(verfers) == 1 and len(digers) == 1
        assert verfers[0].qb64 == ext.signers["h1"][0].verfer.qb64
        # no private key material ever lands in the keystore
        assert ks.pris.get(verfers[0].qb64) is None

        pre = verfers[0].qb64
        pp = ks.prms.get(pre)
        assert pp.algo == Algos.extern
        assert pp.stem == "h1"          # opaque external handle persisted
        assert pp.pidx == 0
        assert mgr.pidx == 1
        ps = ks.sits.get(pre)
        assert ps.new.pubs == [pre]
        assert ps.nxt.pubs == [digers[0].qb64]


def test_manager_extern_incept_duplicate_raises():
    ext = FakeExtern()
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext)
        mgr.incept(algo=Algos.extern, stem="h1", temp=True)
        # same external key handed back again -> already incepted
        ext.incept = lambda **kw: ([ext.signers["h1"][0].verfer], [])
        with pytest.raises(ValueError, match="Already incepted"):
            mgr.incept(algo=Algos.extern, stem="h2", temp=True)


def test_manager_extern_sign_delegates_after_move():
    """After Hab-style .move() old->new pre, sign() by verfers still reaches the module."""
    ext = FakeExtern()
    ser = b"hello extern"
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext)
        verfers, digers = mgr.incept(algo=Algos.extern, stem="h1", temp=True)
        newpre = "E" + "A" * 43
        mgr.move(old=verfers[0].qb64, new=newpre)

        sigers = mgr.sign(ser, verfers=verfers)
        assert len(sigers) == 1
        assert verfers[0].verify(sigers[0].raw, ser)
        assert ext.calls[-1] == ("sign", newpre, "h1")

        sigers = mgr.sign(ser, pubs=[verfers[0].qb64], indexed=False)
        assert isinstance(sigers[0], coring.Cigar)
        assert verfers[0].verify(sigers[0].raw, ser)


def test_manager_extern_sign_without_module_raises():
    ext = FakeExtern()
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext)
        verfers, _ = mgr.incept(algo=Algos.extern, stem="h1", temp=True)
        mgr2 = keeping.Manager(ks=ks)  # same keystore, module not configured
        with pytest.raises(ValueError, match="no extern"):
            mgr2.sign(b"x", verfers=verfers)


def test_manager_non_extern_sign_unchanged():
    ext = FakeExtern()
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext, salt=signing.Salter().qb64)
        verfers, _ = mgr.incept(algo=Algos.salty, temp=True)
        sigers = mgr.sign(b"abc", verfers=verfers)
        assert verfers[0].verify(sigers[0].raw, b"abc")
        assert ext.calls == []


def test_manager_extern_rotate_delegates_and_default_raises():
    ext = FakeExtern()
    with keeping.openKS(temp=True) as ks:
        mgr = keeping.Manager(ks=ks, extern=ext)
        verfers, _ = mgr.incept(algo=Algos.extern, stem="h1", temp=True)
        pre = verfers[0].qb64
        with pytest.raises(NotImplementedError):
            mgr.rotate(pre=pre, temp=True)
        # keystore untouched by a failed rotation
        assert ks.sits.get(pre).new.pubs == [pre]


def test_habery_extern_makehab_end_to_end():
    ext = FakeExtern()
    with habbing.openHby(name="ext", temp=True, extern=ext) as hby:
        assert hby.mgr.extern is ext
        hab = hby.makeHab(name="ext1", algo=Algos.extern, stem="h1", transferable=True)
        assert hab.pre in hby.habs
        assert hab.kever.sn == 0
        assert hab.kever.verfers[0].qb64 == ext.signers["h1"][0].verfer.qb64
        assert hab.algo == Algos.extern

        # signs through the module
        sigers = hab.sign(b"payload")
        assert hab.kever.verfers[0].verify(sigers[0].raw, b"payload")

        # and a normal salty hab on the same Habery is unaffected
        hab2 = hby.makeHab(name="salty1")
        assert hab2.kever.sn == 0


def test_habery_extern_survives_reopen(tmp_path):
    """The module handle is persisted (PrePrm.stem), so a reopened Habery signs with it."""
    ext = FakeExtern()
    kw = dict(name="ext2", base="exttest", temp=False, headDirPath=str(tmp_path), salt=signing.Salter().qb64)
    hby = habbing.Habery(extern=ext, **kw)
    pre = hby.makeHab(name="ext1", algo=Algos.extern, stem="h-persist").pre
    hby.close(clear=False)

    hby2 = habbing.Habery(extern=ext, **kw)
    try:
        hab = hby2.habs[pre]
        sigers = hab.sign(b"again")
        assert ext.calls[-1] == ("sign", pre, "h-persist")
        assert hab.kever.verfers[0].verify(sigers[0].raw, b"again")
    finally:
        hby2.close(clear=True)


def test_habery_without_extern_has_none():
    with habbing.openHby(name="plain", temp=True) as hby:
        assert hby.mgr.extern is None
