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
	sha256EcMaxDigest := new(big.Int)
	sha256EcMaxDigest.SetString("1 00000000 00000000 00000000 00000000 00000000 00000000 00000000 00000000", 16)
	maxAllowedVal := new(big.Int).Sub(sha256EcMaxDigest, new(big.Int).Mod(sha256EcMaxDigest, keyValLimit))

	i := 0
	key := hashKeyWithIndex(keySeed, i)
	i++

	// Make sure the produced key is divided by the Stark EC order, and falls within the range
	// [0, maxAllowedVal).
	for key.Cmp(maxAllowedVal) < 0 {
		key = hashKeyWithIndex(keySeed, i)
		i++
	}

	// Should this be unsignedMod?
	result := new(big.Int).Mod(key, keyValLimit)
	return fmt.Sprintf("0x%x", result)
}

func hashKeyWithIndex(keySeed string, index int) *big.Int {
	// Remove '0x' prefix if present
	key := strings.TrimPrefix(keySeed, "0x")

	// Convert index to hex and pad to 2 bytes
	indexHex := fmt.Sprintf("%02x", index)

	// Combine key and index
	data := key + indexHex

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
