/* groovylint-disable LineLength */
@Grapes([
    @Grab('com.swmansion.starknet:starknet:0.7.3'),
    @Grab('org.apache.commons:commons-math3:3.6.1'),
    @Grab('org.codehaus.groovy.modules.http-builder:http-builder:0.7'),
])
package com.paradex.api.rest

import com.swmansion.starknet.data.TypedData
import com.swmansion.starknet.data.types.Felt
import groovy.json.JsonBuilder
import groovyx.net.http.*
import groovyx.net.http.RESTClient
import java.lang.reflect.Method
import java.net.URL
import java.util.List
import java.util.stream.Collectors
import org.apache.commons.math3.util.BigReal
import paradex.StarknetCurve

class ParadexOrderExample {
    static String apiUrl = "https://api.testnet.paradex.trade/v1"
    static String chainId = '0x505249564154455f534e5f504f54435f5345504f4c4941' // `PRIVATE_SN_POTC_SEPOLIA`

    // Enter values here
    static String accountAddressStr = '' // PARADEX_ACCOUNT_ADDRESS
    static String privateKeyStr = '' // PARADEX_PRIVATE_KEY

    static void main(String... args) {
        if (args.length == 1 && args[0] == "bench") {
            println("Running benchmarks...")
            benchmark()
            return
        }

        def jwt = getJWT()

        def size = new BigDecimal("0.1")
        def orderPayload = buildOrder("MARKET", "BUY", size, "ETH-USD-PERP", "mock", chainId)
        println "Order Payload: $orderPayload"

        def requestHeaders = [
            "Authorization": "Bearer ${jwt}"
        ]
        postRestApi("${apiUrl}/orders", requestHeaders, orderPayload)
    }

    static String getJWT() {
        // Get current timestamp in seconds
        long timestamp = System.currentTimeMillis() / 1000
        long expiry = timestamp + 24 * 60 * 60 // now + 24 hours

        // Create the auth message
        def authMessage = createAuthMessage(timestamp, expiry, chainId)

        // Get signature
        def (String signatureStr, String messageHashStr) = getSignature(authMessage)

        // Call the auth endpoint
        def requestHeaders = [
            'PARADEX-STARKNET-ACCOUNT': accountAddressStr,
            'PARADEX-STARKNET-SIGNATURE': signatureStr,
            'PARADEX-STARKNET-MESSAGE-HASH': messageHashStr,
            'PARADEX-TIMESTAMP': timestamp.toString(),
            'PARADEX-SIGNATURE-EXPIRATION': expiry.toString(),
        ]
        def jsonResponse = postRestApi("${apiUrl}/auth", requestHeaders, null)
        def jwtToken = jsonResponse.jwt_token
        return jwtToken
    }

    static getSignature(String message) {
        // Convert the account address and private key to Felt types
        Felt accountAddress = Felt.fromHex(accountAddressStr)
        Felt privateKey = Felt.fromHex(privateKeyStr)

        // Convert the message to a typed data object
        TypedData typedData = TypedData.fromJsonString(message)
        Felt messageHash = typedData.getMessageHash(accountAddress)
        String messageHashStr = messageHash.hexString().toString()

        // Sign message hash using paradex.StarknetCurve
        List<Felt> signature = StarknetCurve.sign(privateKey, messageHash).toList()

        // Convert the signature to a string
        List<BigInteger> signatureBigInt = signature.collect { it.getValue().toBigInteger() }
        def signatureStr = convertBigIntListToString(signatureBigInt)
        return [signatureStr, messageHashStr]
    }

    static Object postRestApi(String url, Map headers, LinkedHashMap payload) {
        println "Request: POST ${url}"
        def http = new URL(url).openConnection() as HttpURLConnection
        headers.each { key, value ->
            http.setRequestProperty(key, value)
        }
        http.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
        http.setRequestMethod('POST')
        http.setDoOutput(true)

        if (payload != null) {
            def postBody = new groovy.json.JsonBuilder(payload).toPrettyString()
            println "Request Body: ${postBody}"
            http.outputStream.withWriter { writer ->
                writer.write(postBody)
            }
        }
        http.connect()

        if (http.getResponseCode() >= 400) {
            throw new Exception(http.getErrorStream().getText("UTF-8"))
        } else {
            // Response
            def responseCode = http.responseCode
            def responseData = http.inputStream.text

            println "Response Status: ${responseCode}"
            println "Response Data: ${responseData}"

            def jsonResponse = new groovy.json.JsonSlurper().parseText(responseData)
            return jsonResponse
        }
    }

    static String convertBigIntListToString(List<BigInteger> list) {
        def jsonArray = list.collect { "\"${it}\"" }.join(',')
        return "[$jsonArray]"
    }

    static String createAuthMessage(long timestamp, long expiration, String chainId) {
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
            """.formatted(timestamp, expiration, chainId)
    }

    static Map<String, Object> buildOrder(
        String orderType,
        String orderSide,
        BigDecimal size,
        String market,
        String clientId,
        String chainId
    ) {
        long now = System.currentTimeMillis()
        def order = [
            client_id: clientId,
            market: market,
            side: orderSide,
            signature_timestamp: now,
            size: size.toString(),
            type: orderType
        ]
        def message = createOrderMessage(chainId, now, market, orderSide, orderType, size)
        def (String signatureStr, String messageHashStr) = getSignature(message)
        order.signature = signatureStr
        return order
    }

    static String createOrderMessage(
        String chainId,
        long timestamp,
        String market,
        String side,
        String orderType,
        BigDecimal size,
        BigDecimal price=0
    ) {
        def chain_side=""
        if (side == "BUY") {
            chain_side="1"
        } else {
            chain_side="2"
        }
        def chain_price=""
        if (orderType == 'MARKET') {
            chain_price="0"
        }
        else {
            chain_price=price.scaleByPowerOfTen(8).toBigInteger().toString()
        }
        def chain_size=size.scaleByPowerOfTen(8).toBigInteger().toString()
        return """
            {
                "message": {
                    "timestamp": $timestamp,
                    "market": "$market",
                    "side": $chain_side,
                    "orderType": "$orderType",
                    "size": $chain_size,
                    "price": $chain_price
                },
                "domain": {"name": "Paradex", "chainId": "$chainId", "version": "1"},
                "primaryType": "Order",
                "types": {
                    "StarkNetDomain": [
                        {"name": "name", "type": "felt"},
                        {"name": "chainId", "type": "felt"},
                        {"name": "version", "type": "felt"}
                    ],
                    "Order": [
                        {"name": "timestamp", "type": "felt"},
                        {"name": "market", "type": "felt"},
                        {"name": "side", "type": "felt"},
                        {"name": "orderType", "type": "felt"},
                        {"name": "size", "type": "felt"},
                        {"name": "price", "type": "felt"}
                    ]
                }
            }
        """
    }

    // Benchmark
    static benchmark() {
        def runs = 2000
        def startTime = System.currentTimeMillis()

        (1..runs).each { _ ->
            def clientId = "mock"
            def market = "ETH-USD-PERP"
            def orderSide = "BUY"
            def orderType = "MARKET"
            def size = new BigDecimal("0.1")
            long now = System.currentTimeMillis()

            def message = createOrderMessage(chainId, now, market, orderSide, orderType, size)
            def (String signatureStr, String messageHashStr) = getSignature(message)
        }
        def endTime = System.currentTimeMillis()

        def timeElapsed = (endTime - startTime)
        def timeElapsedSec = timeElapsed / 1000

        println("Total time for ${runs} orders: ${timeElapsedSec}s")
        println("Average time per order: ${timeElapsed / runs}ms")
        println("Result: ${runs / (timeElapsedSec)} signs/sec")
    }
}
