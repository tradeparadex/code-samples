# サンプル

## 実行方法

この例は直接実行するか、Dockerで実行することができます。

### 必要条件

Paradexアカウントを制御するためのイーサリアムアカウントの秘密鍵が必要です。[MetaMaskでアカウントの秘密鍵をエクスポートする方法](https://support.metamask.io/hc/en-us/articles/360015289632-How-to-export-an-account-s-private-key)を参照してください。

以下の`ETHEREUM_PRIVATE_KEY`の値を、ご自身の秘密鍵に置き換えることを忘れないでください。

### 直接実行

以下のすべてのコマンドは`examples`ディレクトリから実行してください。

直接実行するには、[Python 3.9+](https://www.python.org/downloads/)がインストールされていることを確認してください。

```bash
python3.9 -m venv .venv # Python 3.9の仮想環境を作成
source .venv/bin/activate
pip install -r requirements.txt # (.venv)
ETHEREUM_PRIVATE_KEY=private_key python onboarding.py # (.venv)
```

#### L2秘密鍵の取得

与えられたL1/イーサリアム秘密鍵に対するL2アカウントの詳細を取得するには、以下のスクリプトを実行できます

```bash
# 前提条件: 仮想環境の作成
ETHEREUM_PRIVATE_KEY=private_key python fetch_l2_account_details.py
```

### Dockerでの実行

[Docker](https://docs.docker.com/get-docker/)が事前にインストールされていることを確認してください。

Dockerイメージをビルドし、Dockerコンテナを実行します。

```bash
docker build -t example .
docker run -it --rm \
  -e ETHEREUM_PRIVATE_KEY=private_key \
  example
```

## オンボーディングと認証

### 概要

この例で行うこと:

* イーサリアムの秘密鍵に基づいて新しいParadexアカウントを生成しオンボーディング
* APIのプライベートエンドポイントにリクエストを行うためのJWTを取得
* JWTを使用してプライベートGET /ordersエンドポイントにリクエストを行う

### スクリプトの注意点

[onboarding.py](onboarding.py#L180)の`main`関数を参照してください。主な流れは:

* オンボーディング
* JWTの取得
* プライベートエンドポイントの呼び出し

### APIの認証にL2認証情報を使用する
オンボーディング後、L2情報を直接使用したい場合は、スクリプトの`Initialize Ethereum`アカウントと`Generate Paradex account`関数をスキップしてください。`eth_private_key_hex`変数の代わりにL2秘密鍵を直接使用すると、実際には使用できない別のアカウントが生成されてしまいます。

なぜか？

これらの関数はL2データを生成する決定論的なプロセスの一部です。L1秘密鍵を使用すると（想定通り）、毎回同じL2データが生成されます。
しかし、異なる情報を与えると、_別の_L2データが生成され、別のアカウントを指すことになります。このようにして情報を取得しようとすると、アカウントが完全に空白であるかのように表示されます。

とはいえ、一度オンボーディングしてL2データを生成すれば（UIからでも）、L2アカウントと秘密鍵を直接プライベートエンドポイントを呼び出す他の関数に組み込むことができ、L1秘密鍵から始めた場合と同じように正しく認証されます。

## 出金

### 概要

この例で行うこと:

* Paradex（ParaclearContract）からL1トークンブリッジコントラクトへの出金
* トランザクションがL1（イーサリアム）で承認されるのを待つ
* L1トークンブリッジコントラクトからL1ウォレットへの出金

### スクリプトの注意点

[withdraw.py](withdraw.py#L111)の`main`関数を参照してください。主な流れは:

* Paradex（ParaclearContract）からの出金
* トランザクションがL1で承認されるのを待つ
  * *注: トランザクションレシートの確認には最大12時間かかる場合があります*
* L1ブリッジからの出金

*注: L1のガス料金は変動する可能性があるため、`maxFeePerGas`と`maxPriorityFeePerGas`を適宜調整してください*

#### イーサリアム（L1）コントラクトのABI

L1コントラクトのABIはEtherscanから取得できます。手順:

1. [Goerli Etherscan](https://goerli.etherscan.io/)にアクセス
2. コントラクトアドレスを検索（または`https://goerli.etherscan.io/address/<address>`）
3. `Contract`タブをクリック
4. `Read as Proxy`タブをクリック
5. 実装コントラクトのABIリンクをクリック
6. `Contract ABI`セクションに移動
7. ABIをJSONファイルに保存

*注: コントラクトはEtherscanでソースコード検証付きでデプロイされている必要があります。*

## 転送（L2）

ParadexのL2アカウントから別のL2アカウントへすべてのUSDCトークンを転送するスクリプトです。

```bash
# 前提条件: 仮想環境の作成
OLD_PARADEX_ACCOUNT_PRIVATE_KEY=private_key NEW_PARADEX_ACCOUNT_PRIVATE_KEY=private_key python transfer_l2_usdc.py
```

### 概要

この例で行うこと:

* Paradex（ParaclearContract）からL2コントラクト（旧）への出金
* L2コントラクト（旧）からL2コントラクト（新）へのUSDCトークンの転送
* L2コントラクト（新）からParadex（ParaclearContract）への入金

### スクリプトの注意点

* 両方のアカウントが事前にオンボーディング例またはUIを通じてオンボーディングされていることを確認してください:
  * `OLD_PARADEX_ACCOUNT_PRIVATE_KEY`（旧アカウントのL2秘密鍵）
  * `NEW_PARADEX_ACCOUNT_PRIVATE_KEY`（新アカウントのL2秘密鍵）
* すべてのUSDC残高を転送するには[transfer_l2_usdc.py](transfer_l2_usdc.py#L29)のデフォルト額を削除してください
  * デフォルト: 100 USDC
* **注意事項:**
  * スクリプトは利用可能なUSDCトークンのみを転送します
  * PnLの実現やオープンポジションのクローズは**行いません**