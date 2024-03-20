package main

import (
	"errors"
	"math/big"

	"github.com/dontpanicdao/caigo"
	"github.com/dontpanicdao/caigo/types"
	"github.com/shopspring/decimal"
)

var scaleX8Decimal = decimal.RequireFromString("100000000")

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

func (o *OrderPayload) GetPrice() string {
	if OrderType(o.OrderType) == OrderTypeMarket {
		return "0"
	} else {
		return o.Price
	}
}

// Multiplies price by decimal precision of 8
// e.g. 3_309.33 is converted to 330_933_000_000 (3_309.33 * 10^8)
func (o *OrderPayload) GetScaledPrice() string {
	return decimal.RequireFromString(o.GetPrice()).Mul(scaleX8Decimal).String()
}

func (o *OrderPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	switch field {
	case "timestamp":
		fmtEnc = append(fmtEnc, big.NewInt(o.Timestamp))
	case "market":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.Market).Big())
	case "side":
		fmtEnc = append(fmtEnc, types.StrToFelt(OrderSide(o.Side).Get()).Big())
	case "orderType":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.OrderType).Big())
	case "size":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.GetScaledSize()).Big())
	case "price":
		fmtEnc = append(fmtEnc, types.StrToFelt(o.GetScaledPrice()).Big())
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
