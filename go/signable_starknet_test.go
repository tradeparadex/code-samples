package main

import (
	"crypto/rand"
	"fmt"
	"math/big"
	"testing"

	"github.com/consensys/gnark-crypto/ecc/stark-curve/ecdsa"
	"github.com/consensys/gnark-crypto/ecc/stark-curve/fp"

	"github.com/dontpanicdao/caigo"
	"github.com/dontpanicdao/caigo/types"
	"github.com/stretchr/testify/require"

	pedersenhash "github.com/consensys/gnark-crypto/ecc/stark-curve/pedersen-hash"
)

var snMessageBigInt = types.UTF8StrToBig("StarkNet Message")

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

func BenchmarkSignSingleOrder(b *testing.B) {
	orderP := &OrderPayload{
		Timestamp: 1684815490129,
		Market:    "ETH-USD-PERP",
		Side:      "SELL",
		OrderType: "LIMIT",
		Size:      "2000000000",   // 20 * 10^8
		Price:     "190000000000", // 1900 * 10^8
	}
	priv, _ := caigo.Curve.GetRandomPrivateKey()
	// priv, _ := big.NewInt(0).SetString("83490221354900822813770954017753999002387366720326019591623250615955802248", 10)
	x, y, err := caigo.Curve.PrivateToPoint(priv)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	// x is the Public Key
	// Replace x with account address
	// Compute using `ComputeAddress` method in `go/utils.go:40`

	var r, s *big.Int
	sum := big.NewInt(0)
	b.ResetTimer()
	var hash *big.Int
	for i := 0; i < b.N; i++ {
		hash, err := GetMessageHash(td, domEnc, x, orderP, sc)
		require.NoError(b, err)
		r, s, err = caigo.Curve.Sign(hash, priv)
		require.NoError(b, err)
		sum = sum.Add(r, s)
	}
	b.StopTimer()
	if hash == nil {
		return
	}

	if caigo.Curve.Verify(hash, r, s, x, y) {
		fmt.Println("signature is valid")
	} else {
		fmt.Println("signature is invalid")
	}
}

func BenchmarkVerifySingleOrder(b *testing.B) {
	orderP := &OrderPayload{
		Timestamp: 1684815490129,
		Market:    "ETH-USD-PERP",
		Side:      "SELL",
		OrderType: "LIMIT",
		Size:      "2000000000",   // 20 * 10^8
		Price:     "190000000000", // 1900 * 10^8
	}
	priv, _ := caigo.Curve.GetRandomPrivateKey()

	pubX, _, err := caigo.Curve.PrivateToPoint(priv)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	// x is the Public Key
	// Replace x with account address
	// Compute using `ComputeAddress` method in `go/utils.go:40`
	// hash, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
	require.NoError(b, err)
	// r, s, err := caigo.Curve.Sign(hash, priv)
	require.NoError(b, err)

	sum := big.NewInt(0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		hash, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
		require.NoError(b, err)
		// valid := caigo.Curve.Verify(hash, r, s, pubX, pubY)
		// require.True(b, valid)
		sum = sum.Add(sum, hash)
	}
}

func PedersenArray(elems []*big.Int) *big.Int {
	fpElements := make([]*fp.Element, len(elems))
	for i, elem := range elems {
		f := &fp.Element{}
		fpElements[i] = f.SetBigInt(elem)
	}
	hash := pedersenhash.PedersenArray(fpElements...)
	res := big.NewInt(0)
	return hash.BigInt(res)
}

func GnarkGetMessageHash(td *caigo.TypedData, domEnc *big.Int, account *big.Int, msg caigo.TypedMessage, sc caigo.StarkCurve) (hash *big.Int, err error) {
	elements := []*big.Int{snMessageBigInt, domEnc, account, nil}

	msgEnc, err := GnarkGetTypedMessageHash(td, td.PrimaryType, msg)
	if err != nil {
		return hash, fmt.Errorf("could not hash message: %w", err)
	}
	elements[3] = msgEnc
	hash = PedersenArray(elements)
	return hash, err
}

func GnarkGetTypedMessageHash(td *caigo.TypedData, inType string, msg caigo.TypedMessage) (hash *big.Int, err error) {
	prim := td.Types[inType]
	elements := []*big.Int{prim.Encoding}

	for _, def := range prim.Definitions {
		if def.Type == "felt" {
			fmtDefinitions := msg.FmtDefinitionEncoding(def.Name)
			elements = append(elements, fmtDefinitions...)
			continue
		} else {
			panic("not felt")
		}
	}
	hash = PedersenArray(elements)
	return hash, err
}

func BenchmarkGnarkSignSingleOrder(b *testing.B) {
	orderP := &OrderPayload{
		Timestamp: 1684815490129,
		Market:    "ETH-USD-PERP",
		Side:      "SELL",
		OrderType: "LIMIT",
		Size:      "2000000000",   // 20 * 10^8
		Price:     "190000000000", // 1900 * 10^8
	}
	priv, err := ecdsa.GenerateKey(rand.Reader)
	pubX := big.NewInt(0)
	pubX = priv.PublicKey.A.X.BigInt(pubX)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	// x is the Public Key
	// Replace x with account address
	// Compute using `ComputeAddress` method in `go/utils.go:40`
	sum := big.NewInt(0)
	b.ResetTimer()
	var sig []byte
	var hash *big.Int
	for i := 0; i < b.N; i++ {

		hash, err := GnarkGetMessageHash(td, domEnc, pubX, orderP, sc)
		// hash2, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
		// fmt.Println(hash.String(), "\n", hash2.String())
		require.NoError(b, err)
		sig, err := priv.Sign(hash.Bytes(), nil)
		require.NoError(b, err)
		valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
		require.Truef(b, valid, "signature is invalid: %v", err)
		sum = sum.Add(sum, hash)
	}
	if hash == nil {
		return
	}
	valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
	require.Truef(b, valid, "signature is invalid: %v", err)
	require.NoError(b, err)
}

func BenchmarkGnarkVerifySingleOrder(b *testing.B) {
	orderP := &OrderPayload{
		Timestamp: 1684815490129,
		Market:    "ETH-USD-PERP",
		Side:      "SELL",
		OrderType: "LIMIT",
		Size:      "2000000000",   // 20 * 10^8
		Price:     "190000000000", // 1900 * 10^8
	}
	priv, err := ecdsa.GenerateKey(rand.Reader)
	pubX := big.NewInt(0)
	pubX = priv.PublicKey.A.X.BigInt(pubX)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)
	// x is the Public Key
	// Replace x with account address
	// Compute using `ComputeAddress` method in `go/utils.go:40`
	hash, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
	require.NoError(b, err)
	sig, err := priv.Sign(hash.Bytes(), nil)
	require.NoError(b, err)
	sum := big.NewInt(0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {

		hash, err := GnarkGetMessageHash(td, domEnc, pubX, orderP, sc)
		// hash2, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
		// fmt.Println(hash.String(), "\n", hash2.String())
		require.NoError(b, err)
		valid, err := priv.PublicKey.Verify(sig, hash.Bytes(), nil)
		require.Truef(b, valid, "signature is invalid: %v", err)
		sum = sum.Add(sum, hash)
	}
}

func TestCompareMessageHash(b *testing.T) {
	orderP := &OrderPayload{
		Timestamp: 1684815490129,
		Market:    "ETH-USD-PERP",
		Side:      "SELL",
		OrderType: "LIMIT",
		Size:      "2000000000",   // 20 * 10^8
		Price:     "190000000000", // 1900 * 10^8
	}
	priv, err := ecdsa.GenerateKey(rand.Reader)
	pubX := big.NewInt(0)
	pubX = priv.PublicKey.A.X.BigInt(pubX)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_SEPOLIA")
	require.NoError(b, err)
	sc := caigo.StarkCurve{}
	domEnc, err := td.GetTypedMessageHash("StarkNetDomain", td.Domain, sc)
	require.NoError(b, err)

	hash, err := GnarkGetMessageHash(td, domEnc, pubX, orderP, sc)
	require.NoError(b, err)
	hash2, err := GetMessageHash(td, domEnc, pubX, orderP, sc)
	require.NoError(b, err)
	require.Equal(b, hash.String(), hash2.String())
}
