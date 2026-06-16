package main

import (
	"math/big"
	"testing"

	"github.com/stretchr/testify/require"
)

// starkEcOrder is the Stark curve order (EC_ORDER) used as the key value limit,
// matching the constant used by paradex-py and paradex.js.
const starkEcOrder = "0800000000000010ffffffffffffffffb781126dcae7b2321e66a241adc64d2f"

func ecOrder(t *testing.T) *big.Int {
	t.Helper()
	n, ok := new(big.Int).SetString(starkEcOrder, 16)
	require.True(t, ok, "failed to parse Stark EC order")
	return n
}

// TestGrindKey pins GrindKey's output to golden values generated from the
// reference implementations (paradex-py / paradex.js grind_key). Any divergence
// in the loop condition, the SHA256_EC_MAX_DIGEST constant, or the seed/index
// hex padding changes the derived key and fails here.
func TestGrindKey(t *testing.T) {
	n := ecOrder(t)

	cases := []struct {
		name string
		seed string
		want string
	}{
		// Typical 64-hex-char seed (the real path derives the seed from the
		// first 32 bytes of an Ethereum signature, i.e. always 64 chars).
		{
			name: "all_a_64",
			seed: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
			want: "0x20c20907b449bacb0a16d9a297ea531aa98eadd80424215dc17da8604868ebf",
		},
		{
			name: "typical",
			seed: "1b2e3d4c5f6a7b8c9d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70819a2b3c4d5e6",
			want: "0x520e4af362957fe86d08d4524b84de5c1d061b3673320863382d95c19365753",
		},
		// Odd-length seed: the reference pads it to even length before hashing.
		// A naive Go port (no padding) panics in hex.DecodeString.
		{
			name: "odd_len",
			seed: "abc",
			want: "0x5fe775158c41e99ecc67b2ebf8d33da7cd3666e6b50a7b5ae761dd5abf993a2",
		},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			got := GrindKey(tc.seed, n)
			require.Equal(t, tc.want, got)
		})
	}
}

// TestGrindKeyAcceptsHexPrefix ensures a "0x"-prefixed seed grinds to the same
// key as the bare seed.
func TestGrindKeyAcceptsHexPrefix(t *testing.T) {
	n := ecOrder(t)
	seed := "1b2e3d4c5f6a7b8c9d0e1f2a3b4c5d6e7f8091a2b3c4d5e6f70819a2b3c4d5e6"
	require.Equal(t, GrindKey(seed, n), GrindKey("0x"+seed, n))
}

// TestGrindKeyInRange checks the produced key is a valid Stark private key,
// i.e. it lies in [0, EC_ORDER).
func TestGrindKeyInRange(t *testing.T) {
	n := ecOrder(t)
	out := GrindKey("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", n)
	key, ok := new(big.Int).SetString(out[2:], 16) // strip "0x"
	require.True(t, ok)
	require.Equal(t, -1, key.Cmp(n), "key must be < EC_ORDER")
	require.GreaterOrEqual(t, key.Sign(), 0, "key must be >= 0")
}
