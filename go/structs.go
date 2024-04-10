package main

type BridgedToken struct {
	Name            string `json:"name"`
	Symbol          string `json:"symbol"`
	Decimals        int    `json:"decimals"`
	L1TokenAddress  string `json:"l1_token_address"`
	L1BridgeAddress string `json:"l1_bridge_address"`
	L2TokenAddress  string `json:"l2_token_address"`
	L2BridgeAddress string `json:"l2_bridge_address"`
}

type SystemConfigResponse struct {
	GatewayUrl                string         `json:"starknet_gateway_url" example:"https://potc-testnet-02.starknet.io"`                                       // Feeder Gateway URL from Starknet
	ChainId                   string         `json:"starknet_chain_id" example:"SN_CHAIN_ID"`                                                                  // Chain ID for the Starknet Instance
	BlockExplorerUrl          string         `json:"block_explorer_url" example:"https://voyager.testnet.paradex.trade/"`                                      // Block explorer URL for the current SN Instance
	ParaclearAddress          string         `json:"paraclear_address" example:"0x4638e3041366aa71720be63e32e53e1223316c7f0d56f7aa617542ed1e7554d"`            // Paraclear contract address
	ParaclearDecimals         int            `json:"paraclear_decimals"`                                                                                       // Decimals used on Paraclear contract
	ParaclearAccountProxyHash string         `json:"paraclear_account_proxy_hash" example:"0x3530cc4759d78042f1b543bf797f5f3d647cde0388c33734cf91b7f7b9314a9"` // Proxy hash of the account contract
	ParaclearAccountHash      string         `json:"paraclear_account_hash" example:"0x033434ad846cdd5f23eb73ff09fe6fddd568284a0fb7d1be20ee482f044dabe2"`      // Class hash of the account contract
	BridgedTokens             []BridgedToken `json:"bridged_tokens"`                                                                                           // Details of the L1, L2 bridge contracts
	L1CoreContractAddress     string         `json:"l1_core_contract_address" example:"0x182FE62c57461d4c5Ab1aE6F04f1D51aA1607daf"`                            // Address of Starknet L1 core contract
	L1OperatorAddress         string         `json:"l1_operator_address" example:"0x63e762538C70442758Fd622116d817761c94FD6A"`                                 // Address of Starknet L1 operator
	L1ChainId                 string         `json:"l1_chain_id" example:"5"`                                                                                  // L1 chain ID value
}

type OnboardingReqBody struct {
	PublicKey string `json:"public_key"`
}

type AuthResBody struct {
	JwtToken string `json:"jwt_token"`
}

type OpenOrdersReqBody struct {
	Market string `json:"market"`
}

type OrderSide string
type OrderType string
type OrderStatus string
type OrderFlag string

type Order struct {
	Id                 string      `json:"id" example:"123456"`                                                                 // Unique order identifier
	Account            string      `json:"account" example:"0x4638e3041366aa71720be63e32e53e1223316c7f0d56f7aa617542ed1e7512x"` // Account identifier (user's account address)
	Market             string      `json:"market" example:"ETH-USD-PERP"`                                                       // Market to which order belongs
	Side               OrderSide   `json:"side"`                                                                                // Order side
	Type               OrderType   `json:"type"`                                                                                // Order type
	Size               string      `json:"size" example:"0.05"`                                                                 // Order size
	RemainingSize      string      `json:"remaining_size" example:"0"`                                                          // Remaining size of the order
	Price              string      `json:"price" example:"26000"`                                                               // Order price
	Status             OrderStatus `json:"status"`                                                                              // Order status
	CreatedAt          int64       `json:"created_at" example:"1681493746016"`                                                  // Order creation time
	LastUpdatedAt      int64       `json:"last_updated_at" example:"1681493746016"`                                             // Order last update time.  No changes once status=CLOSED
	SignatureTimestamp int64       `json:"timestamp" example:"1681493746016"`                                                   // Order signature timestamp
	CancelReason       string      `json:"cancel_reason" example:"NOT_ENOUGH_MARGIN"`                                           // Reason for order cancellation if it was closed by cancel
	ClientId           string      `json:"client_id" example:"x1234"`                                                           // Client id passed on order creation
}

type OpenOrdersRes struct {
	Results []*Order `json:"results"` // Orders list
}

type VerificationType string

var (
	VerificationTypeOnboarding VerificationType = "Onboarding"
	VerificationTypeAuth       VerificationType = "Auth"
	VerificationTypeOrder      VerificationType = "Order"
)

const (
	ORDER_SIDE_BUY  = "BUY"
	ORDER_SIDE_SELL = "SELL"
)

func (s OrderSide) String() string {
	return string(s)
}

func (s OrderSide) Get() string {
	if s == ORDER_SIDE_BUY {
		return "1"
	} else {
		return "2"
	}
}

const (
	OrderTypeMarket OrderType = "MARKET"
	OrderTypeLimit  OrderType = "LIMIT"
)

type OrderRequest struct {
	Market             string      `json:"market" validate:"required" example:"BTC-USD-PERP"` // Market for which order is created
	Side               OrderSide   `json:"side" validate:"required"`                          // Order side
	Type               OrderType   `json:"type" validate:"required"`                          // Order type
	Size               string      `json:"size" validate:"required" example:"1.213"`          // Size of the order
	Price              string      `json:"price" validate:"required" example:"29500.12"`      // Order price
	ClientId           string      `json:"client_id" maxLength:"64" example:"123454321"`      // Unique client assigned ID for the order
	Signature          string      `json:"signature" validate:"required"`                     // Order Payload signed with STARK Private Key
	SignatureTimestamp int64       `json:"signature_timestamp" validate:"required"`           // Timestamp of order creation, used for signature verification
	Instruction        string      `json:"instruction" validate:"required"`                   // Order Instruction, GTC, IOC or POST_ONLY if empty GTC
	Stp                string      `json:"stp"`                                               // Self Trade Prevention, EXPIRE_MAKER, EXPIRE_TAKER or EXPIRE_BOTH, if empty EXPIRE_TAKER
	RecvWindow         int64       `json:"recv_window"`                                       // Order will be created if it is received by API within RecvWindow milliseconds from signature timestamp, minimum is 10 milliseconds
	Flags              []OrderFlag `json:"flags"`                                             // Order flags, allow flag: REDUCE_ONLY
	TriggerPrice       string      `json:"trigger_price"`                                     // Trigger price for stop order
}
