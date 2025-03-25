package main

import (
	"bytes"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/consensys/gnark-crypto/ecc"
	starkcurve "github.com/consensys/gnark-crypto/ecc/stark-curve"
	"github.com/consensys/gnark-crypto/ecc/stark-curve/ecdsa"
	"github.com/consensys/gnark-crypto/ecc/stark-curve/fr"
	"github.com/dontpanicdao/caigo"
	"github.com/dontpanicdao/caigo/types"
	"github.com/ethereum/go-ethereum/crypto"
)

// `GET /system/config`
func GetParadexConfig() (SystemConfigResponse, error) {
	systemConfigUrl := fmt.Sprintf("%s/system/config", PARADEX_HTTP_URL)
	response, err := http.Get(systemConfigUrl)
	if err != nil {
		return SystemConfigResponse{}, err
	}
	responseData, err := io.ReadAll(response.Body)
	if err != nil {
		return SystemConfigResponse{}, err
	}
	var config SystemConfigResponse
	err = json.Unmarshal(responseData, &config)
	if err != nil {
		return SystemConfigResponse{}, err
	}
	return config, nil
}

// Generate Ethereum public key from Ethereum private key
func GetEthereumAccount() (string, string) {
	ethPrivateKey := os.Getenv("ETHEREUM_PRIVATE_KEY")
	privateKeyBytes, _ := crypto.HexToECDSA(ethPrivateKey)
	publicKeyECDSA := &privateKeyBytes.PublicKey
	ethAddress := crypto.PubkeyToAddress(*publicKeyECDSA).Hex()
	return ethPrivateKey, ethAddress
}

// Generate Paradex private key from Ethereum private key
func GenerateParadexAccount(config SystemConfigResponse, ethPrivateKey string) (string, string, string) {
	privateKey, _ := crypto.HexToECDSA(ethPrivateKey)
	ethSignature, _ := SignTypedData(typedData(config.L1ChainId), privateKey)
	// Convert the first 32 bytes of ethSignature to a hex string
	r := hex.EncodeToString(ethSignature[:32])
	// Get Starknet curve order
	n := ecc.STARK_CURVE.ScalarField()
	dexPrivateKey := GrindKey(r, n)
	dexPrivateKeyBN := types.HexToBN(dexPrivateKey)
	dexPublicKeyBN, _, _ := caigo.Curve.PrivateToPoint(dexPrivateKeyBN)
	dexPublicKey := types.BigToHex(dexPublicKeyBN)
	dexAccountAddress := ComputeAddress(config, dexPublicKey)
	return dexPrivateKey, dexPublicKey, dexAccountAddress
}

// Get ECDSA private key from string
func GetEcdsaPrivateKey(pk string) *ecdsa.PrivateKey {
	privateKey := types.StrToFelt(pk).Big()

	// Generate public key
	_, g := starkcurve.Generators()
	ecdsaPublicKey := new(ecdsa.PublicKey)
	ecdsaPublicKey.A.ScalarMultiplication(&g, privateKey)

	// Generate private key
	pkBytes := privateKey.FillBytes(make([]byte, fr.Bytes))
	buf := append(ecdsaPublicKey.Bytes(), pkBytes...)
	ecdsaPrivateKey := new(ecdsa.PrivateKey)
	ecdsaPrivateKey.SetBytes(buf)
	return ecdsaPrivateKey
}

func GnarkSign(messageHash *big.Int, privateKey string) (r, s *big.Int, err error) {
	ecdsaPrivateKey := GetEcdsaPrivateKey(privateKey)
	sigBin, err := ecdsaPrivateKey.Sign(messageHash.Bytes(), nil)
	if err != nil {
		return nil, nil, err
	}
	r = new(big.Int).SetBytes(sigBin[:fr.Bytes])
	s = new(big.Int).SetBytes(sigBin[fr.Bytes:])
	return r, s, nil
}

// `POST /onboarding`
func PerformOnboarding(
	config SystemConfigResponse,
	ethAddress string,
	dexPrivateKey string,
	dexPublicKey string,
	dexAccountAddress string,

) {
	dexAccountAddressBN := types.HexToBN(dexAccountAddress)

	// Get message hash and signature
	sc := caigo.StarkCurve{}
	message := &OnboardingPayload{Action: "Onboarding"}
	typedData, _ := NewVerificationTypedData(VerificationTypeOnboarding, config.ChainId)
	domEnc, _ := typedData.GetTypedMessageHash("StarkNetDomain", typedData.Domain, sc)
	messageHash, _ := GnarkGetMessageHash(typedData, domEnc, dexAccountAddressBN, message, sc)
	r, s, _ := GnarkSign(messageHash, dexPrivateKey)

	// URL
	onboardingUrl := fmt.Sprintf("%s/onboarding", PARADEX_HTTP_URL)

	// Body
	body := OnboardingReqBody{PublicKey: dexPublicKey}
	bodyByte, err := json.Marshal(body)
	if err != nil {
		Print("Unable to marshal body:", err)
	}

	// Request
	req, _ := http.NewRequest(http.MethodPost, onboardingUrl, bytes.NewReader(bodyByte))

	// Headers
	req.Header.Set("Content-Type", CONTENT_TYPE)
	req.Header.Add("PARADEX-ETHEREUM-ACCOUNT", ethAddress)
	req.Header.Add("PARADEX-STARKNET-ACCOUNT", dexAccountAddress)
	req.Header.Add("PARADEX-STARKNET-SIGNATURE", GetSignatureStr(r, s))

	// Response
	res, _ := http.DefaultClient.Do(req)
	Print("POST /onboarding:", res.Status)
}

// `POST /auth`
func GetJwtToken(
	config SystemConfigResponse,
	dexAccountAddress string,
	dexPrivateKey string,
) string {
	dexAccountAddressBN := types.HexToBN(dexAccountAddress)

	// Get timestamp and expiration
	now := time.Now().Unix()
	timestampStr := strconv.FormatInt(now, 10)
	expirationStr := strconv.FormatInt(now+DEFAULT_EXPIRY_IN_SECONDS, 10)

	// Get message hash and signature
	sc := caigo.StarkCurve{}
	message := &AuthPayload{
		Method:     "POST",
		Path:       "/v1/auth",
		Body:       "",
		Timestamp:  timestampStr,
		Expiration: expirationStr,
	}
	typedData, _ := NewVerificationTypedData(VerificationTypeAuth, config.ChainId)
	domEnc, _ := typedData.GetTypedMessageHash("StarkNetDomain", typedData.Domain, sc)
	messageHash, _ := GnarkGetMessageHash(typedData, domEnc, dexAccountAddressBN, message, sc)
	r, s, _ := GnarkSign(messageHash, dexPrivateKey)

	// URL
	authUrl := fmt.Sprintf("%s/auth", PARADEX_HTTP_URL)

	// Request
	req, _ := http.NewRequest(http.MethodPost, authUrl, nil)

	// Headers
	req.Header.Set("Content-Type", CONTENT_TYPE)
	req.Header.Add("PARADEX-STARKNET-ACCOUNT", dexAccountAddress)
	req.Header.Add("PARADEX-STARKNET-SIGNATURE", GetSignatureStr(r, s))
	req.Header.Add("PARADEX-TIMESTAMP", timestampStr)
	req.Header.Add("PARADEX-SIGNATURE-EXPIRATION", expirationStr)

	// Response
	res, _ := http.DefaultClient.Do(req)
	Print("POST /auth:", res.Status)

	jwtToken := ParsePostAuth(res)
	return jwtToken
}

// `GET /orders`
func GetOpenOrders(jwtToken string) []*Order {
	// URL
	ordersUrl := fmt.Sprintf("%s/orders", PARADEX_HTTP_URL)

	// Body
	body := OpenOrdersReqBody{Market: "ETH-USD-PERP"}
	bodyByte, err := json.Marshal(body)
	if err != nil {
		Print("Unable to marshal body:", err)
	}

	// Request
	req, _ := http.NewRequest(http.MethodGet, ordersUrl, bytes.NewReader(bodyByte))

	// Headers
	req.Header.Set("Content-Type", CONTENT_TYPE)
	bearer := fmt.Sprintf("Bearer %s", jwtToken)
	req.Header.Add("Authorization", bearer)

	// Response
	res, _ := http.DefaultClient.Do(req)
	Print("GET /orders:", res.Status)

	orders := ParseGetOrders(res)
	return orders
}

func SubmitOrder(
	config SystemConfigResponse,
	dexAccountAddress string,
	dexPrivateKey string,
	jwtToken string,
) {
	dexAccountAddressBN := types.HexToBN(dexAccountAddress)

	sc := caigo.StarkCurve{}
	typedData, _ := NewVerificationTypedData("Order", config.ChainId)
	domEnc, _ := typedData.GetTypedMessageHash("StarkNetDomain", typedData.Domain, sc)

	// Change order values here
	market := "ETH-USD-PERP"
	side := "BUY"
	orderType := "LIMIT"
	size := "1"
	price := "900"
	timestamp := time.Now().UnixMilli()

	orderPayload := &OrderPayload{
		Timestamp: timestamp,
		Market:    market,
		Side:      side,
		OrderType: orderType,
		Size:      size,
		Price:     price,
	}
	messageHash, _ := GnarkGetMessageHash(typedData, domEnc, dexAccountAddressBN, orderPayload, sc)
	r, s, _ := GnarkSign(messageHash, dexPrivateKey)

	// URL
	ordersUrl := fmt.Sprintf("%s/orders", PARADEX_HTTP_URL)

	// Body
	body := OrderRequest{
		Market:             market,
		Side:               OrderSide(side),
		Type:               OrderType(orderType),
		Size:               size,
		Price:              price,
		Signature:          GetSignatureStr(r, s),
		SignatureTimestamp: timestamp,
	}
	bodyByte, err := json.Marshal(body)
	if err != nil {
		Print("Unable to marshal body:", err)
	}

	// Request
	req, _ := http.NewRequest(http.MethodPost, ordersUrl, bytes.NewReader(bodyByte))

	// Headers
	req.Header.Set("Content-Type", CONTENT_TYPE)
	bearer := fmt.Sprintf("Bearer %s", jwtToken)
	req.Header.Add("Authorization", bearer)

	// Response
	res, _ := http.DefaultClient.Do(req)
	Print("POST /orders:", res.Status)
}

func ExampleSignMultipleOrders() {
	privateKey := GetEcdsaPrivateKey("X")
	accountAddress := big.NewInt(0)
	sc := caigo.StarkCurve{}
	td, _ := NewVerificationTypedData("Order", "PRIVATE_SN_POTC_SEPOLIA")
	domEnc, _ := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)

	for j := 0; j < 10; j++ {
		start := time.Now()
		for i := 0; i < 100000; i++ {
			orderP := &OrderPayload{
				Timestamp: time.Now().UnixMilli(),
				Market:    "ETH-USD-PERP",
				Side:      "SELL",
				OrderType: "LIMIT",
				Size:      strconv.Itoa(4 + i),
				Price:     strconv.Itoa(5900 + i),
			}
			messageHash, _ := GnarkGetMessageHash(td, domEnc, accountAddress, orderP, sc)
			sigBin, err := privateKey.Sign(messageHash.Bytes(), nil)
			if err != nil {
				Print("Error:", err)
			}
			valid, _ := privateKey.PublicKey.Verify(sigBin, messageHash.Bytes(), nil)
			if !valid {
				Print("Invalid signature")
			}
		}
		Print("Average time taken:", time.Since(start).Seconds()/100000)
	}
}

func main() {
	// Load Paradex config
	paradexConfig, _ := GetParadexConfig()

	// Initialize Ethereum account
	ethPrivateKey, ethAddress := GetEthereumAccount()

	// Generate Paradex account from Ethereum private key
	dexPrivateKey, dexPublicKey, dexAccountAddress := GenerateParadexAccount(paradexConfig, ethPrivateKey)

	// Onboard generated Paradex account
	PerformOnboarding(
		paradexConfig,
		ethAddress,
		dexPrivateKey,
		dexPublicKey,
		dexAccountAddress,
	)

	// Get a JWT token to interact with private endpoints
	jwtToken := GetJwtToken(
		paradexConfig,
		dexAccountAddress,
		dexPrivateKey,
	)

	// Submit order using the JWT token
	SubmitOrder(paradexConfig, dexAccountAddress, dexPrivateKey, jwtToken)

	// Get account's open orders using the JWT token
	openOrders := GetOpenOrders(jwtToken)
	openOrdersByte, _ := json.MarshalIndent(openOrders, "", "    ")
	Print(string(openOrdersByte))
}
