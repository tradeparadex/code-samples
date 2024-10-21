package main

import (
	"crypto/ecdsa"
	"fmt"

	"github.com/ethereum/go-ethereum/common"
	"github.com/ethereum/go-ethereum/common/math"
	"github.com/ethereum/go-ethereum/crypto"
	"github.com/ethereum/go-ethereum/signer/core/apitypes"
)

var typesStandard = apitypes.Types{
	"EIP712Domain": {
		{
			Name: "name",
			Type: "string",
		},
		{
			Name: "version",
			Type: "string",
		},
		{
			Name: "chainId",
			Type: "uint256",
		},
	},
	"Constant": {
		{
			Name: "action",
			Type: "string",
		},
	},
}

const primaryType = "Constant"

var domainStandard = apitypes.TypedDataDomain{
	Name:    "Paradex",
	Version: "1",
	ChainId: math.NewHexOrDecimal256(MAINNET_CHAIN_ID),
}

var messageStandard = map[string]interface{}{
	"action": "STARK Key",
}

var typedData = apitypes.TypedData{
	Types:       typesStandard,
	PrimaryType: primaryType,
	Domain:      domainStandard,
	Message:     messageStandard,
}

func SignTypedData(typedData apitypes.TypedData, privateKey *ecdsa.PrivateKey) ([]byte, error) {
	var signature []byte

	hash, err := EncodeForSigning(typedData)
	if err != nil {
		return signature, err
	}
	signature, err = crypto.Sign(hash.Bytes(), privateKey)
	if err != nil {
		return signature, err
	}
	signature[64] += 27

	return signature, nil
}

func EncodeForSigning(typedData apitypes.TypedData) (common.Hash, error) {
	var hash common.Hash

	domainSeparator, err := typedData.HashStruct("EIP712Domain", typedData.Domain.Map())
	if err != nil {
		return hash, err
	}
	typedDataHash, err := typedData.HashStruct(typedData.PrimaryType, typedData.Message)
	if err != nil {
		return hash, err
	}
	rawData := []byte(fmt.Sprintf("\x19\x01%s%s", string(domainSeparator), string(typedDataHash)))
	hash = common.BytesToHash(crypto.Keccak256(rawData))
	return hash, nil
}
