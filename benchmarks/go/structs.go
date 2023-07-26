package auth

type VerificationType string

var (
	VerificationTypeOnboarding VerificationType = "Onboarding"
	VerificationTypeAuth       VerificationType = "Auth"
	VerificationTypeOrder      VerificationType = "Order"
)

type OrderSide string

const (
	ORDER_SIDE_BUY  = "BUY"
	ORDER_SIDE_SELL = "SELL"
)

func (s OrderSide) String() string {
	return string(s)
}

func (s OrderSide) Side() string {
	if s == ORDER_SIDE_BUY {
		return "1"
	} else {
		return "2"
	}
}

type OrderType string

const (
	OrderTypeMarket OrderType = "MARKET"
	OrderTypeLimit  OrderType = "LIMIT"
)
