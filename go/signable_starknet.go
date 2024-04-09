package main

import (
	"errors"
	"fmt"
	"math/big"

	"github.com/consensys/gnark-crypto/ecc/stark-curve/fp"
	"github.com/dontpanicdao/caigo"
	"github.com/dontpanicdao/caigo/types"
	"github.com/shopspring/decimal"

	pedersenhash "github.com/consensys/gnark-crypto/ecc/stark-curve/pedersen-hash"
)

var scaleX8Decimal = decimal.RequireFromString("100000000")
var snMessageBigInt = types.UTF8StrToBig("StarkNet Message")

type OnboardingPayload struct {
	Action string
}

func (o *OnboardingPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	if field == "action" {
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Action).Big())
	}

	return
}

type AuthPayload struct {
	Method     string
	Path       string
	Body       string
	Timestamp  string
	Expiration string
}

func (o *AuthPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	switch field {
	case "method":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Method).Big())
	case "path":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Path).Big())
	case "body":
		// this is required as types.StrToFelt("") returns nil, which seems to be an SN bug
		fmtEnc = append(fmtEnc, big.NewInt(0))
	case "timestamp":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Timestamp).Big())
	case "expiration":
		if o.Expiration != "" {
			fmtEnc = append(fmtEnc, types.StrToFelt(o.Expiration).Big())
		}
	}
	return fmtEnc
}

type OrderPayload struct {
	Timestamp int64  // Unix timestamp in milliseconds when signature was created
	Market    string // Market name - ETH-USD-PERP
	Side      string // 1 for buy, 2 for sell
	OrderType string // MARKET or LIMIT
	Size      string // Size scaled by 1e8
	Price     string // Price scaled by 1e8 (Price is 0 for MARKET orders)
}

// Multiplies size by decimal precision of 8
// e.g. 0.2 is converted to 20_000_000 (0.2 * 10^8)
func (o *OrderPayload) GetScaledSize() string {
	return decimal.RequireFromString(o.Size).Mul(scaleX8Decimal).String()
}

// Multiplies price by decimal precision of 8
// e.g. 3_309.33 is converted to 330_933_000_000 (3_309.33 * 10^8)
func (o *OrderPayload) GetScaledPrice() string {
	price := o.Price
	if OrderType(o.OrderType) == OrderTypeMarket {
		return "0"
	} else {
		return decimal.RequireFromString(price).Mul(scaleX8Decimal).String()
	}
}

func (o *OrderPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	switch field {
	case "timestamp":
		fmtEnc = append(fmtEnc, big.NewInt(o.Timestamp))
	case "market":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Market).Big())
	case "side":
		side := OrderSide(o.Side).Get()
		fmtEnc = append(fmtEnc, types.StrToFelt(side).Big())
	case "orderType":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.OrderType).Big())
	case "size":
		size := o.GetScaledSize()
		fmtEnc = append(fmtEnc, types.StrToFelt(size).Big())
	case "price":
		price := o.GetScaledPrice()
		fmtEnc = append(fmtEnc, types.StrToFelt(price).Big())
	}

	return fmtEnc
}

func domainDefinition() *caigo.TypeDef {
	return &caigo.TypeDef{Definitions: []caigo.Definition{
		{Name: "name", Type: "felt"},
		{Name: "chainId", Type: "felt"},
		{Name: "version", Type: "felt"}}}
}

func domain(chainId string) *caigo.Domain {
	return &caigo.Domain{
		Name:    "Paradex",
		Version: "1",
		ChainId: chainId,
	}
}

func onboardingPayloadDefinition() *caigo.TypeDef {
	return &caigo.TypeDef{Definitions: []caigo.Definition{
		{Name: "action", Type: "felt"}}}
}

func authPayloadDefinition() *caigo.TypeDef {
	return &caigo.TypeDef{Definitions: []caigo.Definition{
		{Name: "method", Type: "felt"},
		{Name: "path", Type: "felt"},
		{Name: "body", Type: "felt"},
		{Name: "timestamp", Type: "felt"},
		{Name: "expiration", Type: "felt"}}}
}

func orderPayloadDefinition() *caigo.TypeDef {
	return &caigo.TypeDef{Definitions: []caigo.Definition{
		{Name: "timestamp", Type: "felt"},
		{Name: "market", Type: "felt"},
		{Name: "side", Type: "felt"},
		{Name: "orderType", Type: "felt"},
		{Name: "size", Type: "felt"},
		{Name: "price", Type: "felt"}}}
}

func onboardingTypes() map[string]caigo.TypeDef {
	return map[string]caigo.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Constant":       *onboardingPayloadDefinition(),
	}
}

func authTypes() map[string]caigo.TypeDef {
	return map[string]caigo.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Request":        *authPayloadDefinition(),
	}
}

func orderTypes() map[string]caigo.TypeDef {
	return map[string]caigo.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Order":          *orderPayloadDefinition(),
	}
}

func NewVerificationTypedData(vType VerificationType, chainId string) (*caigo.TypedData, error) {
	if vType == VerificationTypeOnboarding {
		return NewTypedData(onboardingTypes(), domain(chainId), "Constant")
	}
	if vType == VerificationTypeAuth {
		return NewTypedData(authTypes(), domain(chainId), "Request")
	}
	if vType == VerificationTypeOrder {
		return NewTypedData(orderTypes(), domain(chainId), "Order")
	}
	return nil, errors.New("invalid validation type")
}

// NewTypedData returns a caigo typed data that
// will be used to hash the message. It needs to be the same
// structure the FE sends to metamask snap when signing
func NewTypedData(types map[string]caigo.TypeDef, domain *caigo.Domain, pType string) (*caigo.TypedData, error) {
	typedData, err := caigo.NewTypedData(
		types,
		pType,
		*domain,
	)

	if err != nil {
		return nil, errors.New("failed to create typed data with caigo")
	}

	return &typedData, nil
}

func PedersenArray(elems []*big.Int) *big.Int {
	fpElements := make([]*fp.Element, len(elems))
	for i, elem := range elems {
		fpElements[i] = new(fp.Element).SetBigInt(elem)
	}
	hash := pedersenhash.PedersenArray(fpElements...)
	return hash.BigInt(new(big.Int))
}

func GetMessageHash(td *caigo.TypedData, domEnc *big.Int, account *big.Int, msg caigo.TypedMessage, sc caigo.StarkCurve) (hash *big.Int, err error) {
	elements := []*big.Int{snMessageBigInt, domEnc, account, nil}

	msgEnc, err := td.GetTypedMessageHash(td.PrimaryType, msg, sc)
	if err != nil {
		return hash, fmt.Errorf("could not hash message: %w", err)
	}
	elements[3] = msgEnc
	hash, err = sc.ComputeHashOnElements(elements)
	return hash, err
}

func GnarkGetMessageHash(td *caigo.TypedData, domEnc *big.Int, account *big.Int, msg caigo.TypedMessage, sc caigo.StarkCurve) (hash *big.Int, err error) {
	msgEnc, err := GnarkGetTypedMessageHash(td, td.PrimaryType, msg)
	if err != nil {
		return nil, fmt.Errorf("could not hash message: %w", err)
	}
	elements := []*big.Int{snMessageBigInt, domEnc, account, msgEnc}
	hash = PedersenArray(elements)
	return hash, err
}

func GnarkGetTypedMessageHash(td *caigo.TypedData, inType string, msg caigo.TypedMessage) (hash *big.Int, err error) {
	prim := td.Types[inType]
	elements := make([]*big.Int, 0, len(prim.Definitions)+1)
	elements = append(elements, prim.Encoding)

	for _, def := range prim.Definitions {
		if def.Type == "felt" {
			fmtDefinitions := msg.FmtDefinitionEncoding(def.Name)
			elements = append(elements, fmtDefinitions...)
		} else {
			panic("not felt")
		}
	}
	hash = PedersenArray(elements)
	return hash, err
}
