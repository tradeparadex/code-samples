package main

import (
	"fmt"
	"time"

	"go.blockdaemon.com/pyth"
)

func main() {
	fmt.Println("start...")

	client := pyth.NewClient(pyth.Mainnet, "https://pythnet.rpcpool.com", "wss://pythnet.rpcpool.com")
	stream := client.StreamPriceAccounts()
	// Print updates.
	for update := range stream.Updates() {
		if update.Pubkey.String() == "JBu1AL4obBcCMqKBBxhpWCNUt136ijcuMZLFvTP7iWdB" { // ETH/USD
			fmt.Println(time.Now().Format(time.RFC3339Nano), "ETH: ", update.Agg.Price)
		}
		if update.Pubkey.String() == "GVXRSBjFk6e6J3NbVPXohDJetcTjaeeuykUpbQF8UoMU" { // BTC/USD
			fmt.Println(time.Now().Format(time.RFC3339Nano), "BTC: ", update.Agg.Price)
		}
		if update.Pubkey.String() == "H6ARHf6YXhGYeQfUzQNGk6rDNnLBQKrenN712K4AQJEG" { // SOL/USD
			fmt.Println(time.Now().Format(time.RFC3339Nano), "SOL: ", update.Agg.Price)
		}
		// fmt.Println(update)
	}
}
