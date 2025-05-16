package main

import (
	"errors"
	"fmt"
	"math/big"

	"github.com/NethermindEth/starknet.go/curve"
	"github.com/NethermindEth/starknet.go/typed"
	"github.com/NethermindEth/starknet.go/utils"
	"github.com/shopspring/decimal"
)

var scaleX8Decimal = decimal.RequireFromString("100000000")
var snMessageBigInt = utils.UTF8StrToBig("StarkNet Message")

type OnboardingPayload struct {
	Action string
}

func (o *OnboardingPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	if field == "action" {
		fmtEnc = append(fmtEnc, utils.UTF8StrToBig(o.Action))
	}

	return
}

type AuthPayload struct {
	Method     string
	Path       string
	Body       string
	Timestamp  int64
	Expiration int64
}

func (o *AuthPayload) FmtDefinitionEncoding(field string) (fmtEnc []*big.Int) {
	switch field {
	case "method":
		fmtEnc = append(fmtEnc, utils.UTF8StrToBig(o.Method))
	case "path":
		fmtEnc = append(fmtEnc, utils.UTF8StrToBig(o.Path))
	case "body":
		// this is required as types.StrToFelt("") returns nil, which seems to be an SN bug
		fmtEnc = append(fmtEnc, big.NewInt(0))
	case "timestamp":
		fmtEnc = append(fmtEnc, big.NewInt(o.Timestamp))
	case "expiration":
		if o.Expiration != 0 {
			fmtEnc = append(fmtEnc, big.NewInt(o.Expiration))
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
		fmtEnc = append(fmtEnc, utils.UTF8StrToBig(o.Market))
	case "side":
		side := OrderSide(o.Side).Get()
		fmtEnc = append(fmtEnc, utils.StrToBig(side))
	case "orderType":
		fmtEnc = append(fmtEnc, utils.UTF8StrToBig(o.OrderType))
	case "size":
		size := o.GetScaledSize()
		fmtEnc = append(fmtEnc, utils.StrToBig(size))
	case "price":
		price := o.GetScaledPrice()
		fmtEnc = append(fmtEnc, utils.StrToBig(price))
	}

	return fmtEnc
}

func domainDefinition() *typed.TypeDef {
	return &typed.TypeDef{Definitions: []typed.Definition{
		{Name: "name", Type: "felt"},
		{Name: "chainId", Type: "felt"},
		{Name: "version", Type: "felt"}}}
}

func domain(chainId string) *typed.Domain {
	return &typed.Domain{
		Name:    "Paradex",
		Version: "1",
		ChainId: chainId,
	}
}

func onboardingPayloadDefinition() *typed.TypeDef {
	return &typed.TypeDef{Definitions: []typed.Definition{
		{Name: "action", Type: "felt"}}}
}

func authPayloadDefinition() *typed.TypeDef {
	return &typed.TypeDef{Definitions: []typed.Definition{
		{Name: "method", Type: "felt"},
		{Name: "path", Type: "felt"},
		{Name: "body", Type: "felt"},
		{Name: "timestamp", Type: "felt"},
		{Name: "expiration", Type: "felt"}}}
}

func orderPayloadDefinition() *typed.TypeDef {
	return &typed.TypeDef{Definitions: []typed.Definition{
		{Name: "timestamp", Type: "felt"},
		{Name: "market", Type: "felt"},
		{Name: "side", Type: "felt"},
		{Name: "orderType", Type: "felt"},
		{Name: "size", Type: "felt"},
		{Name: "price", Type: "felt"}}}
}

func onboardingTypes() map[string]typed.TypeDef {
	return map[string]typed.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Constant":       *onboardingPayloadDefinition(),
	}
}

func authTypes() map[string]typed.TypeDef {
	return map[string]typed.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Request":        *authPayloadDefinition(),
	}
}

func orderTypes() map[string]typed.TypeDef {
	return map[string]typed.TypeDef{
		"StarkNetDomain": *domainDefinition(),
		"Order":          *orderPayloadDefinition(),
	}
}

func NewVerificationTypedData(vType VerificationType, chainId string) (*typed.TypedData, error) {
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
func NewTypedData(types map[string]typed.TypeDef, domain *typed.Domain, pType string) (*typed.TypedData, error) {
	typedData, err := typed.NewTypedData(
		types,
		pType,
		*domain,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to create typed data with caigo")
	}

	return &typedData, nil
}

func HashStruct(inType string, typedData typed.TypedData, message typed.TypedMessage) (*big.Int, error) {
	elements := []*big.Int{}
	typeHash, err := typedData.GetTypeHash(inType)
	if err != nil {
		return big.NewInt(0), fmt.Errorf("could not get type hash")
	}
	elements = append(elements, typeHash)
	types := typedData.Types[inType]

	for _, typeDef := range types.Definitions {
		if typeDef.Type == "felt" {
			enc := message.FmtDefinitionEncoding(typeDef.Name)
			elements = append(elements, enc...)
		} else {
			panic("not felt")
		}
	}

	return curve.ComputeHashOnElements(elements), nil
}

func HashTypedData(dexAccountBN *big.Int, typedData typed.TypedData) (*big.Int, error) {
	elements := []*big.Int{snMessageBigInt}
	domEnc, err := HashStruct("StarkNetDomain", typedData, typedData.Domain)
	if err != nil {
		return big.NewInt(0), fmt.Errorf("failed to encode domain")
	}
	elements = append(elements, domEnc)
	elements = append(elements, dexAccountBN)
	messageEnc, err := HashStruct(typedData.PrimaryType, typedData, typedData.Message)
	if err != nil {
		return big.NewInt(0), fmt.Errorf("failed to encode message")
	}
	elements = append(elements, messageEnc)

	return curve.ComputeHashOnElements(elements), nil
}
