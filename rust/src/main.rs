use std::time::Duration;

use log::info;
use paradex::{
    rest::Client,
    structs::{OrderRequest, OrderType, Side},
    url::URL,
};
use rust_decimal::{prelude::FromPrimitive, Decimal};

// Enter your private key here
const PARADEX_PRIVATE_KEY: &str = "<private key hex string>";

#[tokio::main]
async fn main() {
    simple_logger::init_with_level(log::Level::Info).unwrap();

    let url = URL::Testnet;
    let symbol: String = "BTC-USD-PERP".into();

    let mut client_private = Client::new(url, Some(PARADEX_PRIVATE_KEY.into())).await.unwrap();

    info!(
        "Account Information {:?}",
        client_private.account_information().await
    );
    info!("Balance {:?}", client_private.balance().await);
    info!("Positions {:?}", client_private.positions().await);

    let manager = paradex::ws::WebsocketManager::new(
        paradex::url::URL::Testnet,
        Some(client_private),
    )
    .await;
    let orders_id = manager
        .subscribe(
            paradex::ws::Channel::Orders {
                market_symbol: None,
            },
            Box::new(|message| info!("Received order update {message:?}")),
        )
        .await
        .unwrap();
    let fills_id = manager
        .subscribe(
            paradex::ws::Channel::Fills {
                market_symbol: None,
            },
            Box::new(|message| info!("Received fill {message:?}")),
        )
        .await
        .unwrap();
    let position_id = manager
        .subscribe(
            paradex::ws::Channel::Position,
            Box::new(|message| info!("Received position {message:?}")),
        )
        .await
        .unwrap();
    let account_id = manager
        .subscribe(
            paradex::ws::Channel::Account,
            Box::new(|message| info!("Received account {message:?}")),
        )
        .await
        .unwrap();
    let balance_id = manager
        .subscribe(
            paradex::ws::Channel::Balance,
            Box::new(|message| info!("Received balance {message:?}")),
        )
        .await
        .unwrap();

    tokio::time::sleep(Duration::from_secs(2)).await;

    let order_request = OrderRequest {
        instruction: paradex::structs::OrderInstruction::IOC,
        market: symbol,
        price: None,
        side: Side::BUY,
        size: Decimal::from_f64(0.001).unwrap(),
        order_type: OrderType::MARKET,
        client_id: Some("A".into()),
        flags: vec![],
        recv_window: None,
        stp: None,
        trigger_price: None,
    };
    info!("Sending order {order_request:?}");
    let result = client_private.create_order(order_request).await.unwrap();
    info!("Order result {result:?}");

    tokio::time::sleep(Duration::from_secs(5)).await;

    for id in [orders_id, fills_id, position_id, account_id, balance_id] {
        manager.unsubscribe(id).await.unwrap();
    }

    tokio::time::sleep(Duration::from_secs(5)).await;
    manager.stop().await.unwrap();
}
