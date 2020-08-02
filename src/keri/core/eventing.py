# -*- encoding: utf-8 -*-
"""
keri.core.eventing module

"""

import re
import json

from dataclasses import dataclass, astuple
from collections import namedtuple
from base64 import urlsafe_b64encode as encodeB64
from base64 import urlsafe_b64decode as decodeB64
from math import ceil

import cbor2 as cbor
import msgpack
import pysodium
import blake3

from orderedset import OrderedSet as oset

from ..kering import ValidationError, VersionError, EmptyMaterialError, DerivationError
from ..kering import Versionage, Version
from ..help.helping import mdict

from .coring import Versify, Serials, Ilks, CryOneDex
from .coring import Signer, Verfer, Diger, Nexter, Aider, Serder


@dataclass(frozen=True)
class TraitCodex:
    """
    TraitCodex is codex of inception configuration trait code strings
    Only provide defined codes.
    Undefined are left out so that inclusion(exclusion) via 'in' operator works.

    """
    EstOnly:         str = 'EstOnly'  #  Only allow establishment events


    def __iter__(self):
        return iter(astuple(self))

TraitDex = TraitCodex()  # Make instance

Kevage = namedtuple("Kevage", 'serder sigxers')  # Key Event tuple for KELS and DELs

Kevers = dict()  # dict of existing Kevers indexed by aid.qb64 of each Kever

KELs = dict()  # Generator KELs as dict of dicts of events keyed by aid.qb64 then in order by event sn
KERLs = dict()  # Validator KERLs as dict of dicts of events keyed by aid.qb64 then in order by event sn
                # mdict keys must be subclass of str
KELDs = dict()  # Validator KELDs as dict of dicts of events keyed by aid.qb64 then by event dig
DELs = dict()  # Validator DELs as dict of dicts of dup events keyed by aid.qb64 then by event dig
Escrows = dict()  # Validator Escow as dict of dicts of events keyed by aid.qb64 then in order by event sn


def incept( keys,
            version=Version,
            kind=Serials.json,
            sith=None,
            nxt="",
            toad=None,
            wits=None,
            cnfg=None,
            idxs=None
          ):

    """
    Returns serder of inception event.
    Utility function to automate creation of inception events.

     Parameters:
        keys,
        version
        kind
        sith
        nxt
        toad
        wits
        cnfg
        idxs


    """
    vs = Versify(version=version, kind=kind, size=0)
    sn = 0
    ilk = Ilks.icp

    if sith is None:
        sith = max(1, ceil(len(keys) / 2))

    if isinstance(sith, int):
        if sith < 1 or sith > len(keys):  # out of bounds sith
            raise ValueError("Invalid sith = {} for keys = {}".format(sith, keys))
    else:  # list sith not yet supported
        raise ValueError("invalid sith = {}.".format(sith))

    wits = wits if wits is not None else []
    if len(oset(wits)) != len(wits):
        raise ValueError("Invalid wits = {}, has duplicates.".format(wits))

    if toad is None:
        if not wits:
            toad = 0
        else:
            toad = max(1, ceil(len(wits) / 2))

    if wits:
        if toad < 1 or toad > len(wits):  # out of bounds toad
            raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))
    else:
        if toad != 0:  # invalid toad
            raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))

    cnfg = cnfg if cnfg is not None else []

    ked = dict(vs=vs,  # version string
               aid="",  # ab64 prefix
               sn="{:x}".format(sn),  # hex string no leading zeros lowercase
               ilk=ilk,
               sith="{:x}".format(sith), # hex string no leading zeros lowercase
               keys=keys,  # list of qb64
               nxt=nxt,  # hash qual Base64
               toad="{:x}".format(toad),  # hex string no leading zeros lowercase
               wits=wits,  # list of qb64 may be empty
               cnfg=cnfg,  # list of config ordered mappings may be empty
               )

    if idxs is not None:  # add idxs element to ked
        if isinstance(idxs, int):
            idxs="{:x}".format(nsigs)  # single lowercase hex string
        ked["idxs"] = idxs  # update ked with idxs field

    # raises derivation error if non-empty nxt but ephemeral code
    aider = Aider(ked=ked)  # Derive AID from ked
    ked["aid"] = aider.qb64  # update aid element in ked with aid qb64

    return Serder(ked=ked)  # return serialized ked


def rotate( aid,
            keys,
            dig,
            version=Version,
            kind=Serials.json,
            sn=1,
            sith=None,
            nxt="",
            toad=None,
            wits=None, # prior existing wits
            cuts=None,
            adds=None,
            data=None,
            idxs=None
          ):

    """
    Returns serder of rotation event.
    Utility function to automate creation of rotation events.

     Parameters:
        aid
        keys
        dig
        version
        kind
        sn
        sith
        nxt
        toad
        cuts
        adds
        data
        idxs


    """
    vs = Versify(version=version, kind=kind, size=0)
    ilk = Ilks.rot

    if sn < 1:
        raise ValueError("Invalid sn = {} for rot.".format(sn))

    if sith is None:
        sith = max(1, ceil(len(keys) / 2))

    if isinstance(sith, int):
        if sith < 1 or sith > len(keys):  # out of bounds sith
            raise ValueError("Invalid sith = {} for keys = {}".format(sith, keys))
    else:  # list sith not yet supported
        raise ValueError("invalid sith = {}.".format(sith))

    wits = wits if wits is not None else []
    witset = oset(wits)
    if len(witset) != len(wits):
        raise ValueError("Invalid wits = {}, has duplicates.".format(wits))

    cuts = cuts if cuts is not None else []
    cutset = oset(cuts)
    if len(cutset) != len(cuts):
        raise ValueError("Invalid cuts = {}, has duplicates.".format(cuts))

    if (witset & cutset) != cutset:  #  some cuts not in wits
        raise ValueError("Invalid cuts = {}, not all members in wits.".format(cuts))

    adds = adds if adds is not None else []
    addset = oset(adds)
    if len(addset) != len(adds):
        raise ValueError("Invalid adds = {}, has duplicates.".format(adds))

    if cutset & addset:  # non empty intersection
        raise ValueError("Intersecting cuts = {} and  adds = {}.".format(cuts, adds))

    if witset & addset:  # non empty intersection
        raise ValueError("Intersecting wits = {} and  adds = {}.".format(wits, adds))

    newitset = (witset - cutset) | addset

    if len(newitset) != (len(wits) - len(cuts) + len(adds)):  # redundant?
        raise ValueError("Invalid member combination among wits = {}, cuts ={}, "
                         "and adds = {}.".format(wits, cuts, adds))

    if toad is None:
        if not newitset:
            toad = 0
        else:
            toad = max(1, ceil(len(newitset) / 2))

    if newitset:
        if toad < 1 or toad > len(newitset):  # out of bounds toad
            raise ValueError("Invalid toad = {} for resultant wits = {}"
                             "".format(toad, list(newitset)))
    else:
        if toad != 0:  # invalid toad
            raise ValueError("Invalid toad = {} for resultant wits = {}"
                             "".format(toad, list(newitset)))


    data = data if data is not None else []

    ked = dict(vs=vs,  # version string
               aid=aid,  # ab64 prefix
               sn="{:x}".format(sn),  # hex string no leading zeros lowercase
               ilk=ilk,
               dig=dig,
               sith="{:x}".format(sith), # hex string no leading zeros lowercase
               keys=keys,  # list of qb64
               nxt=nxt,  # hash qual Base64
               toad="{:x}".format(toad),  # hex string no leading zeros lowercase
               cuts=cuts,  # list of qb64 may be empty
               adds=adds,  # list of qb64 may be empty
               data=data,  # list of seals
               )

    if idxs is not None:  # add idxs element to ked
        if isinstance(idxs, int):
            idxs="{:x}".format(nsigs)  # single lowercase hex string
        ked["idxs"] = idxs  # update ked with idxs field

    return Serder(ked=ked)  # return serialized ked


def interact( aid,
              dig,
              version=Version,
              kind=Serials.json,
              sn=1,
              data=None,
              idxs=None
          ):

    """
    Returns serder of interaction event.
    Utility function to automate creation of interaction events.

     Parameters:
        aid
        dig
        version
        kind
        sn
        data
        idxs


    """
    vs = Versify(version=version, kind=kind, size=0)
    ilk = Ilks.ixn

    if sn < 1:
        raise ValueError("Invalid sn = {} for ixn.".format(sn))

    data = data if data is not None else []

    ked = dict(vs=vs,  # version string
               aid=aid,  # ab64 prefix
               sn="{:x}".format(sn),  # hex string no leading zeros lowercase
               ilk=ilk,
               dig=dig,
               data=data,  # list of seals
               )

    if idxs is not None:  # add idxs element to ked
        if isinstance(idxs, int):
            idxs="{:x}".format(nsigs)  # single lowercase hex string
        ked["idxs"] = idxs  # update ked with idxs field

    return Serder(ked=ked)  # return serialized ked

class Kever:
    """
    Kever is KERI key event verifier class
    Only supports current version VERSION

    Has the following public attributes and properties:

    Class Attributes:
        .EstOnly is Boolean
                True means allow only establishment events
                False means allow all events

    Attributes:
        .version is version of current event state
        .aider is aider instance of current event state
        .sn is sequence number int
        .diger is Diger instance with digest of current event not prior event
        .ilk is str of current event type
        .sith is int or list of current signing threshold
        .verfers is list of Verfer instances for current event state set of signing keys
        .nexter is qualified qb64 of next sith and next signing keys
        .toad is int threshold of accountable duplicity
        .wits is list of qualified qb64 aids for witnesses
        .cnfg is list of inception configuration data mappings
        .data is list of current seals
        .estOnly is boolean
        .nonTrans is boolean

    Properties:

        .nonTransferable  .nonTrans

    """
    EstOnly = False

    def __init__(self, serder, sigxers, estOnly=None):
        """
        Create incepting kever and state from inception serder
        Verify incepting serder against sigxers raises ValidationError if not

        Parameters:
            serder is Serder instance of inception event
            sigxers is list of SigMat instances of signatures of event
            establishOnly is boolean trait to indicate establish only event

        """
        # update state as we go because if invalid we fail to finish init
        self.version =  serder.version  # version dispatch ?
        self.verfers = serder.verfers  # converts keys to verifiers
        # verify indexes of attached signatures against verifiers
        for sigxer in sigxers:
            if sigxer.index >= len(self.verfers):
                raise ValidationError("Index = {} to large for keys."
                                      "".format(sigxer.index))
            sigxer.verfer = self.verfers[sigxer.index]  # assign verfer

        ked = serder.ked
        sith = ked["sith"]
        if isinstance(sith, str):
            self.sith = int(sith, 16)
            if self.sith < 1 or self.sith > len(self.verfers):  # out of bounds sith
                raise ValueError("Invalid sith = {} for keys = {}".format(sith,
                                      [verfer.qb64 for verfer in self.verfers]))
        else:
            # fix this to support list sith
            raise ValueError("Unsupported type for sith = {}".format(sith))


        if not self.verify(sigxers=sigxers, serder=serder):
            raise ValidationError("Failure verifying signatures = {} for {}"
                                  "".format(sigxers, serder))

        self.aider = Aider(qb64=ked["aid"])
        if not self.aider.verify(ked=ked):  # invalid aid
            raise ValidationError("Invalid aid = {} for inception ked = {}."
                                  "".format(self.aider.qb64, ked))

        self.sn = int(ked["sn"], 16)
        if self.sn != 0:
            raise ValidationError("Invalid sn = {} for inception ked = {}."
                                              "".format(self.sn, ked))
        self.diger =  serder.diger

        ilk = ked["ilk"]
        if ilk != Ilks.icp:
            raise ValidationError("Expected ilk = {} got {}."
                                              "".format(Ilks.icp, ilk))
        self.ilk = ilk

        nxt = ked["nxt"]
        self.nexter = Nexter(qb64=nxt) if nxt else None
        self.nonTrans = True if self.nexter is None else False


        wits = ked["wits"]
        if len(oset(wits)) != len(wits):
            raise ValueError("Invalid wits = {}, has duplicates.".format(wits))
        self.wits = wits

        toad = int(ked["toad"], 16)
        if wits:
            if toad < 1 or toad > len(wits):  # out of bounds toad
                raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))
        else:
            if toad != 0:  # invalid toad
                raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))
        self.toad = toad

        self.cnfg = ked["cnfg"]
        self.data = None

        # ensure boolean
        self.estOnly = (True if (estOnly if estOnly is not None else self.EstOnly)
                             else False)
        for d in self.cnfg:
            if "trait" in d and d["trait"] == TraitDex.EstOnly:
                self.estOnly = Tru

        # update logs
        kevage = Kevage(serder=serder, sigxers=sigxers)
        aid = self.aider.qb64
        dig = self.diger.qb64

        if aid not in Kevers:
            Kevers[aid] = dict()
        Kevers[aid][dig] = self
        if aid not in KERLs:
            KERLs[aid] = mdict()  # supports recover forks by sn
        KERLs[aid].add(ked["sn"], kevage)  # multiple values each sn hex str
        if aid not in KELDs:
            KELDs[aid] = dict()
        KELDs[aid][dig] = kevage


    def update(self, serder,  sigxers):
        """
        Not original inception event. So verify event serder and
        signatures sigxers and update state

        """
        if self.nonTrans:  # nonTransferable so no events after inception allowed
            raise ValidationError("Attept to add event in nontransferable state.")

        # if rotation event use keys from event
        # if interaction event use keys from existing Kever
        ked = serder.ked
        ilk = ked["ilk"]

        if ilk == Ilks.rot:  # subsequent rotation event
            # verify nxt from prior
            # also check derivation code of aid for non-transferable
            #  check and

            if self.nexter is None:   # empty so rotations not allowed
                raise ValidationError("Attempted rotation for nontransferable"
                                      " aid = {}".format(self.aider.qb64))

            verfers = serder.verfers  # only for establishment events

            sith = ked["sith"]
            if isinstance(sith, str):
                sith = int(sith, 16)
                if sith < 1 or sith > len(self.verfers):  # out of bounds sith
                    raise ValueError("Invalid sith = {} for keys = {}".format(sith,
                                          [verfer.qb64 for verfer in verfers]))
            else:
                # fix this to support list sith
                raise ValueError("Unsupported type for sith = {}".format(sith))

            keys = ked["keys"]
            if not self.nexter.verify(sith=sith, keys=keys):
                raise ValidationError("Mismatch nxt digest = {} with rotation"
                                      " sith = {}, keys = {}.".format(nexter.qb64))

            # prior nxt valid so verify sigxers using new verifier keys from event
            # verify indexes of attached signatures against verifiers
            for sigxer in sigxers:
                if sigxer.index >= len(verfers):
                    raise ValidationError("Index = {} to large for keys."
                                          "".format(sigxer.index))
                sigxer.verfer = verfers[sigxer.index]  # assign verfer

            if not self.verify(sigxers=sigxers, serder=serder, sith=sith):
                raise ValidationError("Failure verifying signatures = {} for {}"
                                  "".format(sigxers, serder))

            # compute wits from cuts and adds use set
            # verify set math
            witset = oset(self.wits)
            cuts = ked["cuts"]
            cutset = oset(cuts)
            if len(cutset) != len(cuts):
                raise ValueError("Invalid cuts = {}, has duplicates.".format(cuts))

            if (witset & cutset) != cutset:  #  some cuts not in wits
                raise ValueError("Invalid cuts = {}, not all members in wits.".format(cuts))


            adds = ked["adds"]
            addset = oset(adds)
            if len(addset) != len(adds):
                raise ValueError("Invalid adds = {}, has duplicates.".format(adds))

            if cutset & addset:  # non empty intersection
                raise ValueError("Intersecting cuts = {} and  adds = {}.".format(cuts, adds))

            if witset & addset:  # non empty intersection
                raise ValueError("Intersecting wits = {} and  adds = {}.".format(self.wits, adds))

            wits = list((witset - cutset) | addset)

            if len(wits) != (len(self.wits) - len(cuts) + len(adds)):  # redundant?
                raise ValueError("Invalid member combination among wits = {}, cuts ={}, "
                                 "and adds = {}.".format(self.wits, cuts, adds))

            toad = int(ked["toad"], 16)
            if wits:
                if toad < 1 or toad > len(wits):  # out of bounds toad
                    raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))
            else:
                if toad != 0:  # invalid toad
                    raise ValueError("Invalid toad = {} for wits = {}".format(toad, wits))


            # nxt and signatures verify so update state
            self.sn = int(ked["sn"], 16)
            self.diger = serder.diger
            self.ilk = ilk
            self.sith = sith
            self.verfers = verfers
            # update .nexter
            nxt = ked["nxt"]
            self.nexter = Nexter(qb64=nxt) if nxt else None  # check for empty
            if self.nexter is None:
                self.nonTrans = True

            self.toad = toad
            self.wits = wits
            self.data = ked["data"]

            # update logs
            kevage = Kevage(serder=serder, sigxers=sigxers)
            aid = self.aider.qb64
            dig = self.diger.qb64
            KERLs[aid].add(ked["sn"], kevage)  # multiple values each sn hex str
            KELDs[aid][self.diger.qb64] = kevage


        elif ilk == Ilks.ixn:  # subsequent interaction event
            if self.estOnly:
                raise ValidationError("Unexpected non-establishment event = {}."
                                  "".format(serder))

            # use prior .verfers
            # verify indexes of attached signatures against verifiers
            for sigxer in sigxers:
                if sigxer.index >= len(self.verfers):
                    raise ValidationError("Index = {} to large for keys."
                                          "".format(sigxer.index))
                sigxer.verfer = self.verfers[sigxer.index]  # assign verfer

            if not self.verify(sigxers=sigxers, serder=serder):
                raise ValidationError("Failure verifying signatures = {} for {}"
                                  "".format(sigxers, serder))

            # update state
            self.sn = int(ked["sn"], 16)
            self.diger = serder.diger
            self.ilk = ilk

            # update logs
            kevage = Kevage(serder=serder, sigxers=sigxers)
            aid = self.aider.qb64
            dig = self.diger.qb64
            KERLs[aid].add(ked["sn"], kevage)  # multiple values each sn hex str
            KELDs[aid][self.diger.qb64] = kevage


        else:  # unsupported event ilk so discard
            raise ValidationError("Unsupported ilk = {}.".format(ilk))


    def verify(self, sigxers, serder, sith=None):
        """
        Use verfer in each sigxer to verify signature against serder with sith
        Assumes that sigxers with verfer already extracted correctly wrt indexes
        If sith not provided then use .sith instead

        Parameters:
            sigxers is list of Sigxer instances
            serder is Serder instance
            sith is int threshold

        """
        sith = sith if sith is not None else self.sith

        for sigxer in sigxers:
            if not sigxer.verfer.verify(sigxer.raw, serder.raw):
                return False

        if not isinstance(sith, int):
            raise ValueError("Unsupported type for sith ={}".format(sith))
        if len(sigxers) < sith:  # not meet threshold fix for list sith
            return False

        return True





class Kevery:
    """
    Kevery is Kever (KERI key event verifier) instance factory which are
    extracted from a key event stream of event and attached signatures

    Only supports current version VERSION

    Has the following public attributes and properties:

    Attributes:

    Properties:

    """
    def __init__(self):
        """
        Set up event stream

        """


    def processAll(self, kes):
        """

        """
        if not isinstance(kes, bytearray):  # destructive processing
            kes = bytearray(kes)

        while kes:
            try:
                serder, sigxers = self.extractOne(kes=kes)
            except Exception as ex:
                # log diagnostics errors etc
                # error extracting means bad key event stream
                del kes[:]  #  delete rest of stream
                continue

            try:
                self.processOne(serder=serder, sigxers=sigxers)
            except Exception as  ex:
                # log diagnostics errors etc
                continue


    def processOne(self, serder, sigxers):
        """
        Process one event serder with attached indexd signatures sigxers

        Parameters:
            kes is bytearray of serialized key event stream.
                May contain one or more sets each of a serialized event with
                attached signatures.

        """
        # fetch ked ilk  aid, sn, dig to see how to process
        ked = serder.ked
        try:
            aider = Aider(qb64=ked["aid"])
        except Exception as ex:
            raise ValidationError("Invalid aid = {}.".format(ked["aid"]))
        aid = aider.qb64
        ked = serder.ked
        ilk = ked["ilk"]
        try:
            sn = int(ked["sn"], 16)
        except Exception as ex:
            raise ValidationError("Invalid sn = {}".format(ked["sn"]))
        dig = serder.dig

        if aid not in Kevers:  #  first seen event for aid
            if ilk == Ilks.icp:  # first seen and inception so verify event keys
                # kever init verifies basic inception stuff and signatures
                # raises exception if problem adds to KEL Kevers
                kever = Kever(serder=serder, sigxers=sigxers)  # create kever from serder

            else:  # not inception so can't verify, add to escrow
                # log escrowed
                if aid not in Escrows:  #  add to Escrows
                    Escrows[aid] = mdict()  # multiple values by sn
                if sn not in Escrows[aid]:
                    Escrows[aid].add(sn, Kevage(serder=serder, sigxers=sigxers))


        else:  # already accepted inception event for aid
            if dig in KELDs["aid"]:  #  duplicate event so dicard
                # log duplicate
                return  # discard

            if ilk == Ilks.icp:  # inception event so maybe duplicitous
                # kever init verifies basic inception stuff and signatures
                # raises exception if problem
                kever = Kever(serder=serder, sigxers=sigxers)  # create kever from serder

                #  verified duplicitous event log it and add to DELS if first time
                if aid not in DELs:  #  add to DELS
                    DELs[aid] = dict()
                if dig not in DELS[aid]:
                    DELS[aid][dig] = Kevage(serder=serder, sigxers=sigxers)

            else:
                kever = Kevers[aid]  # get existing kever for aid
                # if sn not subsequent to prior event  else escrow
                if sn <= kever.sn:  # stale event
                    # log stale event
                    return  # discard

                if sn > kever.sn + 1:  # sn not in order
                    #  log escrowed
                    if aid not in Escrows:  #  add to Escrows
                        Escrows[aid] = mdict()  # multiple values by sn
                    if sn not in Escrows[aid]:
                        Escrows[aid].add(sn, Kevage(serder=serder, sigxers=sigxers))

                else:  # sn == kever.sn + 1
                    if dig != kever.diger:  # prior event dig not match
                        raise ValidationError("Mismatch prior dig = {} with"
                                              " current = {}.".format(dig,
                                                                      kever.diger))

                    # verify signatures etc and update state if valid
                    # raise exception if problem. adds to KELs
                    kever.update(serder=serder, sigxers=sigxers)


    def extractOne(self, kes):
        """
        Extract one event with attached signatures from key event stream kes
        Returns: (serder, sigxers)

        Parameters:
            kes is bytearray of serialized key event stream.
                May contain one or more sets each of a serialized event with
                attached signatures.

        """
        # deserialize packet from kes
        try:
            serder = Serder(raw=kes)
        except Exception as ex:
            raise ValidationError("Error while processing key event stream"
                                  " = {}".format(ex))

        version = serder.version
        if version != Version:  # This is where to dispatch version switch
            raise VersionError("Unsupported version = {}, expected {}."
                                  "".format(version, Version))

        del kes[:srdr.size]  # strip off event from front of kes

        # extract attached sigs as Sigxers
        sigxers = []  # list of Sigxer instances for attached indexed signatures
        if "idxs" in ked and ked["idxs"]: # extract signatures given indexes
            indexes = ked["idxs"]
            if isinstance(indexes, str):
                nsigs = int(indexes, 16)
                if nsigs < 1:
                    raise ValidationError("Invalid number of attached sigs = {}."
                                              " Must be > 1 if not empty.".format(nsigs))

                for i in range(nsigs): # extract each attached signature
                    # check here for type of attached signatures qb64 or qb2
                    sigxer = Sigxer(qb64=kes)  #  qb64
                    sigxers.append(sigxer)
                    del kes[:len(sigxer.qb64)]  # strip off signature

            elif isinstance(indexes, list):
                if len(set(indexes)) != len(indexes):  # duplicate index(es)
                    raise ValidationError("Duplicate indexes in sigs = {}."
                                              "".format(indexes))

                for index in indexes:
                    # check here for type of attached signatures qb64 or qb2
                    sigxer = SigMat(qb64=kes)  #  qb64
                    sigxers.append(sigxer)
                    del kes[:len(sigxer.qb64)]  # strip off signature

                    if index != sigxer.index:
                        raise ValidationError("Mismatching signature index = {}"
                                              " with index = {}".format(sigxer.index,
                                                                        index))
            else:
                raise ValidationError("Invalid format of indexes = {}."
                                          "".format(indexes))

        else:  # no info on attached sigs
            pass
            #  check flag if should parse rest of stream for attached sigs
            #  or should parse for index block

        if not sigxers:
            raise ValidationError("Missing attached signature(s).")

        return (serder, sigxers)
