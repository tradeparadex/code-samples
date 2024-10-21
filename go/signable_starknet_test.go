package main

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"testing"
	"time"

	"github.com/consensys/gnark-crypto/ecc/stark-curve/ecdsa"

	"github.com/dontpanicdao/caigo"
	"github.com/stretchr/testify/require"
)

const StarknetChainID = "PRIVATE_SN_POTC_SEPOLIA" // TESTNET

var orderPayload = &OrderPayload{
	Timestamp: time.Now().UnixMilli(),
	Market:    "ETH-USD-PERP",
	Side:      "SELL",
	OrderType: "LIMIT",
	Size:      "4",
	Price:     "5900",
}
var testAccountAddress = big.NewInt(0) // Replace with account address

func BenchmarkSignSingleOrder(b *testing.B) {
	priv, _ := caigo.Curve.GetRandomPrivateKey()
	x, y, err := caigo.Curve.PrivateToPoint(priv)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, StarknetChainID)
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)

	var r, s *big.Int
	sum := big.NewInt(0)
	b.ResetTimer()
	var hash *big.Int
	for i := 0; i < b.N; i++ {
		hash, err = GetMessageHash(td, domEnc, testAccountAddress, orderPayload, sc)
		require.NoError(b, err)
		r, s, err = caigo.Curve.Sign(hash, priv)
		require.NoError(b, err)
		sum = sum.Add(r, s)
	}
	b.StopTimer()

	if hash != nil {
		valid := caigo.Curve.Verify(hash, r, s, x, y)
		fmt.Println("Valid signature:", valid)
	}
}

func BenchmarkVerifySingleOrder(b *testing.B) {
	priv, err := caigo.Curve.GetRandomPrivateKey()
	require.NoError(b, err)
	pubX, _, err := caigo.Curve.PrivateToPoint(priv)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, StarknetChainID)
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)

	sum := big.NewInt(0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		hash, err := GetMessageHash(td, domEnc, pubX, orderPayload, sc)
		require.NoError(b, err)
		sum = sum.Add(sum, hash)
	}
}

func BenchmarkGnarkSignSingleOrder(b *testing.B) {
	priv, err := ecdsa.GenerateKey(rand.Reader)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, StarknetChainID)
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	sum := big.NewInt(0)
	b.ResetTimer()
	var sig []byte
	var hash *big.Int
	for i := 0; i < b.N; i++ {
		hash, err = GnarkGetMessageHash(td, domEnc, testAccountAddress, orderPayload, sc)
		require.NoError(b, err)
		sig, err = priv.Sign(hash.Bytes(), nil)
		require.NoError(b, err)
		valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
		require.Truef(b, valid, "signature is invalid: %v", err)
		sum = sum.Add(sum, hash)
	}
	valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
	require.Truef(b, valid, "signature is invalid: %v", err)
	require.NoError(b, err)
}

func BenchmarkGnarkVerifySingleOrder(b *testing.B) {
	priv, err := ecdsa.GenerateKey(rand.Reader)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, StarknetChainID)
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	hash, err := GnarkGetMessageHash(td, domEnc, testAccountAddress, orderPayload, sc)
	require.NoError(b, err)
	sig, err := priv.Sign(hash.Bytes(), nil)
	require.NoError(b, err)
	sum := big.NewInt(0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		hash, err := GnarkGetMessageHash(td, domEnc, testAccountAddress, orderPayload, sc)
		require.NoError(b, err)
		valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
		require.Truef(b, valid, "signature is invalid: %v", err)
		sum = sum.Add(sum, hash)
	}
}

func TestCompareMessageHash(b *testing.T) {
	priv, err := ecdsa.GenerateKey(rand.Reader)
	pubX := big.NewInt(0)
	pubX = priv.PublicKey.A.X.BigInt(pubX)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)

	hash, err := GnarkGetMessageHash(td, domEnc, pubX, orderPayload, sc)
	require.NoError(b, err)
	hash2, err := GetMessageHash(td, domEnc, pubX, orderPayload, sc)
	require.NoError(b, err)
	require.Equal(b, hash.String(), hash2.String())
}
