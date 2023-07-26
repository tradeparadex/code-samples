package main

import (
	"encoding/json"
	"fmt"
	"io"
	"math/big"
	"net/http"
	"os"
)

func Print(str string) {
	s := fmt.Sprintln(str)
	io.WriteString(os.Stdout, s)
}

func GetSignatureStr(r, s *big.Int) string {
	signature := []string{r.String(), s.String()}
	signatureByte, _ := json.Marshal(signature)
	return string(signatureByte)
}

func ParsePostAuth(res *http.Response) string {
	body, _ := io.ReadAll(res.Body)
	var authResBody AuthResBody
	json.Unmarshal(body, &authResBody)
	return authResBody.JwtToken
}

func ParseGetOrders(res *http.Response) []*Order {
	body, _ := io.ReadAll(res.Body)
	var getOpenOrdersRes OpenOrdersRes
	json.Unmarshal(body, &getOpenOrdersRes)
	return getOpenOrdersRes.Results
}
