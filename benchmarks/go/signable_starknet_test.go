package auth

import (
	"fmt"
	"math/big"
	"testing"

	"github.com/dontpanicdao/caigo"
	"github.com/stretchr/testify/require"
)

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

	x, y, err := caigo.Curve.PrivateToPoint(priv)
	require.NoError(b, err)
	td, err := NewVerificationTypedData(VerificationTypeOrder, "PRIVATE_SN_POTC_GOERLI")
	require.NoError(b, err)
	// x is the Public Key
	// Replace x with account address
	// Compute using `ComputeAddress` method in `examples/go/utils.go:40`
	hash, err := td.GetMessageHash(x, orderP, caigo.StarkCurve{})
	require.NoError(b, err)
	var r, s *big.Int
	sum := big.NewInt(0)
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		r, s, err = caigo.Curve.Sign(hash, priv)
		require.NoError(b, err)
		sum = sum.Add(r, s)
	}

	if caigo.Curve.Verify(hash, r, s, x, y) {
		fmt.Println("signature is valid")
	} else {
		fmt.Println("signature is invalid")
	}
}
