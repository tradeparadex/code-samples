export interface SystemConfig {
  readonly apiBaseUrl: string;
  readonly starknet: {
    readonly chainId: string;
  };
}

export interface Account {
  address: string;
  publicKey: string;
  ethereumAccount: string;
  privateKey: string;
  jwtToken?: string;
}
