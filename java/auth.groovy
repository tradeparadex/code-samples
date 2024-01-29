@Grapes([
    @Grab(group='com.swmansion.starknet', module='starknet', version='0.7.3'),
    @Grab(group='org.apache.commons', module='commons-math3', version='3.6.1'),
    @Grab(group='org.codehaus.groovy.modules.http-builder', module='http-builder', version='0.7'),
])
package com.paradex.api.rest

import com.swmansion.starknet.data.TypedData
import com.swmansion.starknet.data.types.Felt
import com.swmansion.starknet.signer.StarkCurveSigner
import groovy.json.JsonBuilder
import groovyx.net.http.*
import groovyx.net.http.RESTClient
import java.lang.reflect.Method
import java.net.URL
import java.util.List
import java.util.stream.Collectors
import org.apache.commons.math3.util.BigReal

class ParadexAuthExample {
    static void main(String... args) {
        // Enter values here
        String accountAddressStr = '' // PARADEX_ACCOUNT_ADDRESS
        String privateKeyStr = '' // PARADEX_PRIVATE_KEY

        // Convert the account address and private key to Felt types
        Felt accountAddress = Felt.fromHex(accountAddressStr)
        Felt privateKey = Felt.fromHex(privateKeyStr)

        // Get current timestamp in seconds
        long timestamp = System.currentTimeMillis() / 1000
        long expiry = timestamp + 24 * 60 * 60 // now + 24 hours

        // Chain ID - PRIVATE_SN_POTC_SEPOLIA
        BigInteger chainID = new BigInteger('7693264728749915528729180568779831130134670232771119425')
        String chainIdHex = '0x' + chainID.toString(16).toUpperCase()

        // Create the auth message
        def authMessage = createAuthMessage(timestamp, expiry, chainIdHex)

        // Convert the auth message to a typed data object
        TypedData typedData = TypedData.fromJsonString(authMessage)
        Felt messageHash = typedData.getMessageHash(accountAddress)

        // Create new StarkCurveSigner with the private key
        StarkCurveSigner scSigner = new StarkCurveSigner(privateKey)

        // Sign the typed data
        List<Felt> signature = scSigner.signTypedData(typedData, accountAddress)

        // Convert the signature to a string
        List<BigInteger> signatureBigInt = signature.collect { it.getValue().toBigInteger() }
        def signatureStr = convertBigIntListToString(signatureBigInt)

        // Call the auth endpoint
        def apiUrl = 'https://api.testnet.paradex.trade/v1/auth/'
        def requestHeaders = [
            'PARADEX-STARKNET-ACCOUNT': accountAddressStr,
            'PARADEX-STARKNET-SIGNATURE': signatureStr,
            'PARADEX-STARKNET-MESSAGE-HASH': messageHash.hexString().toString(),
            'PARADEX-TIMESTAMP': timestamp.toString(),
            'PARADEX-SIGNATURE-EXPIRATION': expiry.toString(),
        ]
        postRestApi(apiUrl, requestHeaders)
    }

    static void postRestApi(String url, Map headers) {
        println "Sending request..."
        def connection = new URL(url).openConnection()
        headers.each { key, value ->
            connection.setRequestProperty(key, value)
        }
        connection.setRequestMethod('POST')
        connection.setDoOutput(true)

        // Response
        println "Response status: ${connection.responseCode}"
        println "Response output: ${connection.inputStream.text}"
    }

    static String convertBigIntListToString(List<BigInteger> list) {
        def jsonArray = list.collect { "\"${it}\"" }.join(',')
        return "[$jsonArray]"
    }

    static String createAuthMessage(long timestamp, long expiration, String chainIdHex) {
        return """
           {
                "message": {
                    "method": "POST",
                    "path": "/v1/auth",
                    "body": "",
                    "timestamp": %s,
                    "expiration": %s
                },
                "domain": {"name": "Paradex", "chainId": "%s", "version": "1"},
                "primaryType": "Request",
                "types": {
                    "StarkNetDomain": [
                        {"name": "name", "type": "felt"},
                        {"name": "chainId", "type": "felt"},
                        {"name": "version", "type": "felt"}
                    ],
                    "Request": [
                        {"name": "method", "type": "felt"},
                        {"name": "path", "type": "felt"},
                        {"name": "body", "type": "felt"},
                        {"name": "timestamp", "type": "felt"},
                        {"name": "expiration", "type": "felt"}
                    ]
                }
            }
            """.formatted(timestamp, expiration, chainIdHex)
    }
}
