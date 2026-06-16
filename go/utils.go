package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"os"
	"strings"

	"github.com/dontpanicdao/caigo"
	"github.com/dontpanicdao/caigo/types"
)

func Print(str ...any) {
	s := fmt.Sprintln(str...)
	io.WriteString(os.Stdout, s)
}

func GetSignatureStr(r, s *big.Int) string {
	signature := []string{r.String(), s.String()}
	signatureByte, _ := json.Marshal(signature)
	return string(signatureByte)
}

func ParsePostAuth(res *http.Response) string {
	body, _ := io.ReadAll(res.Body)
	var authResBody AuthResBody
	json.Unmarshal(body, &authResBody)
	return authResBody.JwtToken
}

func ParseGetOrders(res *http.Response) []*Order {
	body, _ := io.ReadAll(res.Body)
	var getOpenOrdersRes OpenOrdersRes
	json.Unmarshal(body, &getOpenOrdersRes)
	return getOpenOrdersRes.Results
}

func ComputeAddress(config SystemConfigResponse, publicKey string) string {
	publicKeyBN := types.HexToBN(publicKey)

	paraclearAccountHashBN := types.HexToBN(config.ParaclearAccountHash)
	paraclearAccountProxyHashBN := types.HexToBN(config.ParaclearAccountProxyHash)

	zero := big.NewInt(0)
	initializeBN := types.GetSelectorFromName("initialize")

	contractAddressPrefix := types.StrToFelt("STARKNET_CONTRACT_ADDRESS").Big()

	constructorCalldata := []*big.Int{
		paraclearAccountHashBN,
		initializeBN,
		big.NewInt(2),
		publicKeyBN,
		zero,
	}
	constructorCalldataHash, _ := caigo.Curve.ComputeHashOnElements(constructorCalldata)

	address := []*big.Int{
		contractAddressPrefix,
		zero,        // deployer address
		publicKeyBN, // salt
		paraclearAccountProxyHashBN,
		constructorCalldataHash,
	}
	addressHash, _ := caigo.Curve.ComputeHashOnElements(address)
	return types.BigToHex(addressHash)
}

func GrindKey(keySeed string, keyValLimit *big.Int) string {
	// SHA256_EC_MAX_DIGEST is 2^256, the size of the SHA-256 output space.
	sha256EcMaxDigest := new(big.Int).Lsh(big.NewInt(1), 256)
	maxAllowedVal := new(big.Int).Sub(sha256EcMaxDigest, new(big.Int).Mod(sha256EcMaxDigest, keyValLimit))

	i := 0
	key := hashKeyWithIndex(keySeed, i)
	i++

	// Make sure the produced key is divided by the Stark EC order, and falls within the range
	// [0, maxAllowedVal). Keep grinding while the key is out of range (>= maxAllowedVal).
	for key.Cmp(maxAllowedVal) >= 0 {
		key = hashKeyWithIndex(keySeed, i)
		i++
	}

	// Should this be unsignedMod?
	result := new(big.Int).Mod(key, keyValLimit)
	return fmt.Sprintf("0x%x", result)
}

// paddedHex returns the hex string with a leading '0' prepended when its length
// is odd, ensuring it decodes to a whole number of bytes.
func paddedHex(h string) string {
	if len(h)%2 != 0 {
		return "0" + h
	}
	return h
}

func hashKeyWithIndex(keySeed string, index int) *big.Int {
	// Remove '0x' prefix if present
	key := strings.TrimPrefix(keySeed, "0x")

	// Combine key and index, each padded to an even number of hex digits so the
	// concatenation decodes cleanly to bytes (matching the reference padded_hex).
	data := paddedHex(key) + paddedHex(fmt.Sprintf("%x", index))

	// Decode hex string to bytes
	dataBytes, err := hex.DecodeString(data)
	if err != nil {
		panic(err)
	}

	// Compute SHA-256 hash
	hash := sha256.Sum256(dataBytes)

	// Convert hash to big.Int
	return new(big.Int).SetBytes(hash[:])
}
