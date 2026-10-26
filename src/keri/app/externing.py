# -*- encoding: utf-8 -*-
"""
KERI
keri.app.externing module

Plug-in point for externally managed keys (HSM, remote signing service, ...)
used with keeping.Algos.extern.
"""
from ..core import coring


class ExternModule:
    """Base class for external key management.

    The Manager never sees private key material for an Algos.extern identifier.
    It hands key creation and signing to an instance of a subclass of this
    class, supplied via Manager(extern=...) or Habery(extern=...).

    Opaque handle: the caller of Manager.incept may pass ``stem`` (e.g. through
    Habery.makeHab(algo=Algos.extern, stem=handle)). The Manager persists it in
    the keystore PrePrm.stem and passes it back as ``stem`` on every later
    call, so the module can locate the external key for the identifier even
    after a process restart.
    """

    def incept(self, stem=None, icodes=None, icount=1,
               icode=coring.MtrDex.Ed25519_Seed, ncodes=None, ncount=1,
               ncode=coring.MtrDex.Ed25519_Seed, dcode=coring.MtrDex.Blake3_256,
               transferable=True, temp=False, **kwa):
        """Create keys on the external device.

        Returns:
            tuple: (verfers, digers) where verfers is list of current key
                Verfer and digers is list of next key digest Diger
        """
        raise NotImplementedError

    def rotate(self, pre, stem=None, ncodes=None, ncount=1,
               ncode=coring.MtrDex.Ed25519_Seed, dcode=coring.MtrDex.Blake3_256,
               transferable=True, temp=False, **kwa):
        """Rotate keys on the external device.

        Returns:
            tuple: (verfers, digers) of the new current keys and next digests
        """
        raise NotImplementedError

    def sign(self, ser, pre=None, stem=None, pubs=None, verfers=None,
             indexed=True, indices=None, ondices=None, **kwa):
        """Sign ser using the external device.

        Returns:
            list: Siger instances if indexed else Cigar instances
        """
        raise NotImplementedError
