#!/bin/bash

# To run this script you need to run the following 2 commands in separate terminals:
#   > kli agent vlei
#   > kli witness demo
# and from the vLEI repo run:
#   > vLEI-server -s ./schema/acdc -c ./samples/acdc/ -o ./samples/oobis/
#
echo "KERI_SCRIPT_DIR=" +${KERI_SCRIPT_DIR}
echo "KERI_DEMO_SCRIPT_DIR=" +${KERI_DEMO_SCRIPT_DIR}
# Alias variables
GLEIF_AID_ALIAS="gleif"
PROVENANT_QVI_AID_ALIAS="provenant-qvi"
PROVENANT_VETTER_AID_ALIAS="provenant-vetter"
SYNIVERSE_AID_ALIAS="syniverse"
BRAND_AID_ALIAS="brand"
# Registry variables
GLEIF_AID_REGISTRY="gleif-registry"
PROVENANT_QVI_AID_REGISTRY="provenant-qvi-registry"
PROVENANT_VETTER_AID_REGISTRY="provenant-vetter-registry"
SYNIVERSE_AID_REGISTRY="syniverse-registry"
BRAND_AID_REGISTRY="brand-registry"

echo ">> create/unlock GLEIF wallet"
# # EHmR-f9oRqtJEkIkxzClhjc84Aqbp5dylK1Ugn8bEt7Y - gleif
curl -s -X POST "http://localhost:5625/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"GLEIF\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"salt\":\"0ACDEyMzQ1Njc4OWxtbm9GhI\"}" | jq
sleep 1
curl -s -X PUT "http://localhost:5625/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"GLEIF\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
sleep 5
echo ">> Create GLEIF AID"
GLEIF_AID=$(curl -s -X POST "http://localhost:5625/ids/$GLEIF_AID_ALIAS" -H "accept: */*" -H "Content-Type: application/json" -d "{\"transferable\":true,\"wits\":[\"BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha\", \"BLskRTInXnMxWaGqcpSyMgo0nYbalW99cGZESrz3zapM\",\"BIKKuvBwpmDVA4Ds-EpL5bt9OqPzWPja2LigFYZN2YfX\"],\"toad\":3, \"icount\":1,\"ncount\":1,\"isith\":1,\"nsith\":1}" | jq -r '.d' )
echo "GLEIF AID : $GLEIF_AID"

echo ">> create/unlock Provenant wallet"
# # ECVKeYAbQkmCLy4gnr8suhQzYOykvxDrVANZhE4Fp-iq - provenant-qvi
# # ELaFLtjX-v1-tpTzIfMAFEhCMepcfYjP9_CHyl53B7ZC - provenant-vetter
curl -s -X POST "http://localhost:5627/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Provenant\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"salt\":\"0ACDEyMzQ1Njc4OWxtbm9aBc\"}" | jq
sleep 1
curl -s -X PUT "http://localhost:5627/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Provenant\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
sleep 5
echo ">> Create Provenant-QVI AID"
PROVENANT_QVI_AID=$(curl -s -X POST "http://localhost:5627/ids/$PROVENANT_QVI_AID_ALIAS" -H "accept: */*" -H "Content-Type: application/json" -d "{\"transferable\":true,\"wits\":[\"BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha\", \"BLskRTInXnMxWaGqcpSyMgo0nYbalW99cGZESrz3zapM\",\"BIKKuvBwpmDVA4Ds-EpL5bt9OqPzWPja2LigFYZN2YfX\"],\"toad\":3, \"icount\":1,\"ncount\":1,\"isith\":1,\"nsith\":1}" | jq -r '.d' )
echo "PROVENANT_QVI_AID : $PROVENANT_QVI_AID"

echo ">> Create Provenant-Vetter AID"
PROVENANT_VETTER_AID=$(curl -s -X POST "http://localhost:5627/ids/$PROVENANT_VETTER_AID_ALIAS" -H "accept: */*" -H "Content-Type: application/json" -d "{\"transferable\":true,\"wits\":[\"BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha\", \"BLskRTInXnMxWaGqcpSyMgo0nYbalW99cGZESrz3zapM\",\"BIKKuvBwpmDVA4Ds-EpL5bt9OqPzWPja2LigFYZN2YfX\"],\"toad\":3, \"icount\":1,\"ncount\":1,\"isith\":1,\"nsith\":1}" | jq -r '.d' )
echo "PROVENANT_VETTER_AID : $PROVENANT_VETTER_AID"

echo "create/unlock Syniverse wallet"
# # EEkzBv05zN33PdaTlkw97D2haVj2WPFVlKymPhcjYCT9 - syniverse
curl -s -X POST "http://localhost:5628/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Syniverse\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"salt\":\"0ACDEyMzQ1Njc4OWxtbm9AbC\"}" | jq
sleep 1
curl -s -X PUT "http://localhost:5628/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Syniverse\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
sleep 5
echo ">> Create Syniverse AID"
SYNIVERSE_AID=$(curl -s -X POST "http://localhost:5628/ids/$SYNIVERSE_AID_ALIAS" -H "accept: */*" -H "Content-Type: application/json" -d "{\"transferable\":true,\"wits\":[\"BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha\", \"BLskRTInXnMxWaGqcpSyMgo0nYbalW99cGZESrz3zapM\",\"BIKKuvBwpmDVA4Ds-EpL5bt9OqPzWPja2LigFYZN2YfX\"],\"toad\":3, \"icount\":1,\"ncount\":1,\"isith\":1,\"nsith\":1}" | jq -r '.d' )
echo "SYNIVERSE_AID : $SYNIVERSE_AID"

echo "create/open Brand wallet" 
# # EJOnVfxUKTtx2Ol_seuRfcBNu0rvrIZN4q7InQ3E1OeV - Brand
curl -s -X POST "http://localhost:5629/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Brand\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"salt\":\"0ACDEyMzQ1Njc4OWxtbm9dEf\"}" | jq
sleep 1
curl -s -X PUT "http://localhost:5629/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Brand\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
sleep 5
echo ">> Create Brand AID"
BRAND_AID=$(curl -s -X POST "http://localhost:5629/ids/$BRAND_AID_ALIAS" -H "accept: */*" -H "Content-Type: application/json" -d "{\"transferable\":true,\"wits\":[\"BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha\", \"BLskRTInXnMxWaGqcpSyMgo0nYbalW99cGZESrz3zapM\",\"BIKKuvBwpmDVA4Ds-EpL5bt9OqPzWPja2LigFYZN2YfX\"],\"toad\":3, \"icount\":1,\"ncount\":1,\"isith\":1,\"nsith\":1}" | jq -r '.d' )
echo "Brand AID : $BRAND_AID"

echo 'create registries'
sleep 3
curl -s -X POST "http://localhost:5625/registries" -H "accept: */*" -H "Content-Type: application/json" -d "{\"alias\":\"$GLEIF_AID_ALIAS\",\"baks\":[],\"estOnly\":false,\"name\":\"$GLEIF_AID_REGISTRY\",\"noBackers\":true,\"toad\":0}" | jq
curl -s -X POST "http://localhost:5627/registries" -H "accept: */*" -H "Content-Type: application/json" -d "{\"alias\":\"$PROVENANT_QVI_AID_ALIAS\",\"baks\":[],\"estOnly\":false,\"name\":\"$PROVENANT_QVI_AID_REGISTRY\",\"noBackers\":true,\"toad\":0}" | jq
curl -s -X POST "http://localhost:5627/registries" -H "accept: */*" -H "Content-Type: application/json" -d "{\"alias\":\"$PROVENANT_VETTER_AID_ALIAS\",\"baks\":[],\"estOnly\":false,\"name\":\"$PROVENANT_VETTER_AID_REGISTRY\",\"noBackers\":true,\"toad\":0}" | jq
curl -s -X POST "http://localhost:5628/registries" -H "accept: */*" -H "Content-Type: application/json" -d "{\"alias\":\"$SYNIVERSE_AID_ALIAS\",\"baks\":[],\"estOnly\":false,\"name\":\"$SYNIVERSE_AID_REGISTRY\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"noBackers\":true,\"toad\":0}" | jq
curl -s -X POST "http://localhost:5629/registries" -H "accept: */*" -H "Content-Type: application/json" -d "{\"alias\":\"$BRAND_AID_ALIAS\",\"baks\":[],\"estOnly\":false,\"name\":\"$BRAND_AID_REGISTRY\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\",\"noBackers\":true,\"toad\":0}" | jq
sleep 5

# oobi variables
GLEIF_AID_OOBI="http://127.0.0.1:5642/oobi/$GLEIF_AID/witness/BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha"
PROVENANT_QVI_AID_OOBI="http://127.0.0.1:5642/oobi/$PROVENANT_QVI_AID/witness/BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha"
PROVENANT_VETTER_AID_OOBI="http://127.0.0.1:5642/oobi/$PROVENANT_VETTER_AID/witness/BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha"
SYNIVERSE_AID_OOBI="http://127.0.0.1:5642/oobi/$SYNIVERSE_AID/witness/BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha"
BRAND_AID_OOBI="http://127.0.0.1:5642/oobi/$BRAND_AID/witness/BBilc4-L3tFUnfM_wJr4S4OJanAv_VmF_dJNN6vkf2Ha"

echo 'Resolving gleif oobi'
sleep 3
curl -s -X POST "http://localhost:5627/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$GLEIF_AID_ALIAS\", \"url\":\"$GLEIF_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5628/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$GLEIF_AID_ALIAS\", \"url\":\"$GLEIF_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5629/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$GLEIF_AID_ALIAS\", \"url\":\"$GLEIF_AID_OOBI\"}" | jq

echo 'Resolving Provenant-QVI oobi'
curl -s -X POST "http://localhost:5625/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_QVI_AID_ALIAS\", \"url\":\"$PROVENANT_QVI_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5627/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_QVI_AID_ALIAS\", \"url\":\"$PROVENANT_QVI_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5628/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_QVI_AID_ALIAS\", \"url\":\"$PROVENANT_QVI_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5629/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_QVI_AID_ALIAS\", \"url\":\"$PROVENANT_QVI_AID_OOBI\"}" | jq

echo 'Resolving Provenant-Vetter oobi'
curl -s -X POST "http://localhost:5625/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_VETTER_AID_ALIAS\", \"url\":\"$PROVENANT_VETTER_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5627/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_VETTER_AID_ALIAS\", \"url\":\"$PROVENANT_VETTER_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5628/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_VETTER_AID_ALIAS\", \"url\":\"$PROVENANT_VETTER_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5629/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$PROVENANT_VETTER_AID_ALIAS\", \"url\":\"$PROVENANT_VETTER_AID_OOBI\"}" | jq

echo 'Resolving Syniverse oobi'
sleep 3
curl -s -X POST "http://localhost:5625/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$SYNIVERSE_AID_ALIAS\", \"url\":\"$SYNIVERSE_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5627/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$SYNIVERSE_AID_ALIAS\", \"url\":\"$SYNIVERSE_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5629/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$SYNIVERSE_AID_ALIAS\", \"url\":\"$SYNIVERSE_AID_OOBI\"}" | jq

echo 'Resolving Brand oobi'
sleep 3
curl -s -X POST "http://localhost:5625/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$BRAND_AID_ALIAS\", \"url\":\"$BRAND_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5627/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$BRAND_AID_ALIAS\", \"url\":\"$BRAND_AID_OOBI\"}" | jq
curl -s -X POST "http://localhost:5628/oobi" -H "accept: */*" -H "Content-Type: application/json" -d "{\"oobialias\": \"$BRAND_AID_ALIAS\", \"url\":\"$BRAND_AID_OOBI\"}" | jq

RULES=`cat ${KERI_DEMO_SCRIPT_DIR}/data/rules.json`

echo 'GLEIF issues qvi credential to Provenant-QVI'
curl -s -X POST "http://localhost:5625/credentials/$GLEIF_AID_ALIAS" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"credentialData\":{\"LEI\":\"984500983AD71E4FBC41\"},\"recipient\":\"$PROVENANT_QVI_AID\",\"registry\":\"$GLEIF_AID_REGISTRY\",\"schema\":\"EBfdlu8R27Fbx-ehrqwImnK-8Cm79sqbAQ4MmvEAYqao\",\"rules\":$RULES}"  | jq
sleep 8
echo "Provenant-QVI retrieves Credentials..."
curl -s -X GET "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS?type=received" -H "accept: application/json"  | jq
sleep 3

echo 'Issue LE credential from Provenant-QVI to Provenant-Vetter - have to create the edges first'
PROVENANT_QVI_CRED_SAID=$(curl -s -X GET "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS?type=received" -H "accept: application/json" -H "Content-Type: application/json" | jq '.[0] | .sad.d')
echo $PROVENANT_QVI_CRED_SAID | jq -f ${KERI_DEMO_SCRIPT_DIR}/data/legal-entity-edges-filter.jq  > /tmp/legal-entity-edges.json
LE_EDGES=`cat /tmp/legal-entity-edges.json`
#RULES=`cat ${KERI_DEMO_SCRIPT_DIR}/data/rules.json`
curl -s -X POST "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"credentialData\":{\"LEI\":\"984500983AD71E4FBC41\"},\"recipient\":\"$PROVENANT_VETTER_AID\",\"registry\":\"$PROVENANT_QVI_AID_REGISTRY\",\"schema\":\"ENPXp1vQzRF6JwIuS-mp2U8Uf1MoADoP_GqQ62VsDZWY\",\"source\":$LE_EDGES,\"rules\":$RULES}" | jq
sleep 8

# echo "Provenant-Vetter  retrieves Credentials..."
# curl -s -X GET "http://localhost:5627/credentials/$PROVENANT_VETTER_AID_ALIAS?type=received" -H "accept: application/json" | jq
# sleep 3

echo 'Issue LE credential from Provenant-QVI to Syniverse'
# PROVENANT_QVI_CRED_SAID=$(curl -s -X GET "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS?type=received" -H "accept: application/json" -H "Content-Type: application/json" | jq '.[0] | .sad.d')
# echo $PROVENANT_QVI_CRED_SAID | jq -f ${KERI_DEMO_SCRIPT_DIR}/data/legal-entity-edges-filter.jq  > /tmp/legal-entity-edges.json
# LE_EDGES=`cat /tmp/legal-entity-edges.json`
# RULES=`cat ${KERI_DEMO_SCRIPT_DIR}/data/rules.json`
curl -s -X POST "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"credentialData\":{\"LEI\":\"549300CYZBHMZC8VLL59\"},\"recipient\":\"$SYNIVERSE_AID\",\"registry\":\"$PROVENANT_QVI_AID_REGISTRY\",\"schema\":\"ENPXp1vQzRF6JwIuS-mp2U8Uf1MoADoP_GqQ62VsDZWY\",\"source\":$LE_EDGES,\"rules\":$RULES}" | jq
sleep 8

echo 'Issue LE credential from Provenant-QVI to Brand'
# PROVENANT_QVI_CRED_SAID=$(curl -s -X GET "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS?type=received" -H "accept: application/json" -H "Content-Type: application/json" | jq '.[0] | .sad.d')
# echo $PROVENANT_QVI_CRED_SAID | jq -f ${KERI_DEMO_SCRIPT_DIR}/data/legal-entity-edges-filter.jq  > /tmp/legal-entity-edges.json
# LE_EDGES=`cat /tmp/legal-entity-edges.json`
# RULES=`cat ${KERI_DEMO_SCRIPT_DIR}/data/rules.json`
curl -s -X POST "http://localhost:5627/credentials/$PROVENANT_QVI_AID_ALIAS" -H "accept: application/json" -H "Content-Type: application/json" -d "{\"credentialData\":{\"LEI\":\"549300GCXOZ91IQ06J16\"},\"recipient\":\"$BRAND_AID\",\"registry\":\"$PROVENANT_QVI_AID_REGISTRY\",\"schema\":\"ENPXp1vQzRF6JwIuS-mp2U8Uf1MoADoP_GqQ62VsDZWY\",\"source\":$LE_EDGES,\"rules\":$RULES}" | jq
sleep 8

echo 'REGISTER ENTERPRISES  in custodial service'
# Register Provenant in custodial service
Provenant_Enterprise_Id=$(curl -s -X  POST 'http://localhost:9082/enterprises' -H 'Content-Type: application/json' -d '{"name": "Provenant", "legalEntityIdentifier": "984500983AD71E4FBC41", "keriAgentEndpoint": "http://localhost:5627", "role": "PlatformOwner"}'  | jq -r '.id' )
echo "Provenant_Enterprise_Id : $Provenant_Enterprise_Id"

# Register Syniverse in custodial service
Syniverse_Enterprise_Id=$(curl -s -X  POST 'http://localhost:9082/enterprises' -H 'Content-Type: application/json' -d '{"name": "Syniverse", "legalEntityIdentifier": "549300CYZBHMZC8VLL59", "keriAgentEndpoint": "http://localhost:5628", "role": "DirectConnectAggregator"}' | jq -r '.id' )
echo "Syniverse_Enterprise_Id : $Syniverse_Enterprise_Id"

# Register Brand in custodial service
Brand_Enterprise_Id=$(curl -s -X  POST 'http://localhost:9082/enterprises' -H 'Content-Type: application/json' -d '{"name": "Subway", "legalEntityIdentifier": "549300GCXOZ91IQ06J16", "keriAgentEndpoint": "http://localhost:5629", "role": "Brand"}' | jq -r '.id' )
echo "Brand_Enterprise_Id : $Brand_Enterprise_Id"

echo 'REGISTER AIDs  in custodial service'
# Insert Provenant-QVI AID to Custodial Service
curl -s -X POST "http://localhost:9082/enterprises/$Provenant_Enterprise_Id/identifiers" -H 'Content-Type: application/json' \
-d "{\"aid\": \"$PROVENANT_QVI_AID\", \"alias\": \"$PROVENANT_QVI_AID_ALIAS\", \"oobi\": \"$PROVENANT_QVI_AID_OOBI\", \"credentialRegistry\": \"$PROVENANT_QVI_AID_REGISTRY\"}"

# Insert Provenant-QVI AID to Custodial Service
curl -s -X POST "http://localhost:9082/enterprises/$Provenant_Enterprise_Id/identifiers" -H 'Content-Type: application/json' \
-d "{\"aid\": \"$PROVENANT_VETTER_AID\", \"alias\": \"$PROVENANT_VETTER_AID_ALIAS\", \"oobi\": \"$PROVENANT_VETTER_AID_OOBI\", \"credentialRegistry\": \"$PROVENANT_VETTER_AID_REGISTRY\"}"

# Insert Syniverse AID to Custodial Service
curl -s -X POST "http://localhost:9082/enterprises/$Syniverse_Enterprise_Id/identifiers" -H 'Content-Type: application/json' \
-d "{\"aid\": \"$SYNIVERSE_AID\", \"alias\": \"$SYNIVERSE_AID_ALIAS\", \"oobi\": \"$SYNIVERSE_AID_OOBI\", \"credentialRegistry\": \"$SYNIVERSE_AID_REGISTRY\"}"

# Insert Brand AID to Custodial Service
curl -s -X POST "http://localhost:9082/enterprises/$Brand_Enterprise_Id/identifiers" -H 'Content-Type: application/json' \
-d "{\"aid\": \"$BRAND_AID\", \"alias\": \"$BRAND_AID_ALIAS\", \"oobi\": \"$BRAND_AID_OOBI\", \"credentialRegistry\": \"$BRAND_AID_REGISTRY\"}"


# Unlock Agents
# curl -s -X PUT "http://localhost:5625/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"GLEIF\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
# curl -s -X PUT "http://localhost:5627/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Provenant\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
# curl -s -X PUT "http://localhost:5628/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Syniverse\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq
# curl -s -X PUT "http://localhost:5629/boot" -H "accept: */*" -H "Content-Type: application/json" -d "{\"name\":\"Brand\",\"passcode\":\"DoB2-6Fj4x-9Lbo-AFWJr-a17O\"}" | jq