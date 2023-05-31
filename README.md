# voucher-trade-assets DApp

This DApp is a coin toss game between two players. The purpose of this example is to illustrate the cycle of Layer-1 to Layer-2 to Layer-1 again. The smart contract in the contracts folder handles the game logic, and the Cartesi Machine is the game "engine" (coin toss). After the machine runs the game and decides on the winner, it generates a voucher to send the result back to Layer-1 when executed. The game workflow is as follows:

1. The player calls the `play` method of the `voucher-trade-assets` contract passing his opponent's address to create a game.
2. The opponent calls the same `play` method passing the challenger's address. Now that both players decided to play, the algorithm will generate randomness and send an input to the Cartesi Rollups with the players and the randomness.^
3. Inside the Cartesi Machine the game between the players is run using the randomness provided as seed. Once the winner is settled, the Cartesi DApp generates a voucher.
4. Waits for the epoch and the dispute period to end so the voucher can be validated and executed.^^
5. Execute the voucher.^^^


^ The Cartesi Machine is devoid of any source of entropy for it to be deterministic, so an external randomness is needed.

^^ Since Cartesi Rollups is an Optimistic Rollup solution, we need to wait for the dispute period to end so the state of the DApp is persisted. After that, vouchers can be executed to trigger changes in layer-1.

^^^ When executed, the voucher triggers the `announce_winner` function of the `voucher-trade-assets` contract. This function updates the structure that stores the game, emits a `GameResult` event, and increments the game counter for the players. In case they decide to start a new game.


## Requirements

Please refer to the [rollups-examples requirements](https://github.com/cartesi/rollups-examples/tree/main/README.md#requirements).

To interact with the DApp in testnet the following is also needed:
1. [Metamask Plugin](https://metamask.io/)

## Contracts

The DApp uses only one smart contract, the different versions provided differ only in how the randomness is generated. The one in the local directory uses de block hash as randomness and is suitable for local tests (**Do not use such a thing in production**). The other uses [Chainlink](https://docs.chain.link/getting-started/conceptual-overview), an external network that provides trusted randomness for Blockchain. The approach using Chainlink needs different contracts for different networks since it has to request the randomness from a Chainlink contract deployed on the same network.

### Deploying Smart Contracts

The easiest way to deploy a smart contract is through the [Remix IDE](https://remix.ethereum.org), so the proceedings are:

1. Creat a `voucher-trade-assets.sol` in the contracts directory of the Remix IDE worspace.
2. Copy the choosen smart contract code and paste it into the one created in the Remix IDE workspace.
3. Compile the contract (Ctrl + s).
4. Click on the Tab "Deploy & run transactions".
5. Select the environment/network you want to deploy.
    1. If you are running locally, make sure to run the `docker compose` command first to bring up the test environment.
6. Click on `deploy`.

## Building

To build the application, run the following command:

```shell
docker buildx bake -f docker-bake.hcl -f docker-bake.override.hcl --load
```

## Running

To start the application, execute the following command:

```shell
docker compose up
```

The application can afterwards be shut down with the following command:

```shell
docker compose down -v
```

### Deploying DApps

Deploying a new Cartesi DApp to a blockchain requires creating a smart contract on that network, as well as running a validator node for the DApp.

The first step is to build the DApp's back-end machine, which will produce a hash that serves as a unique identifier.

```shell
docker buildx bake -f docker-bake.hcl -f docker-bake.override.hcl machine --load
```

Once the machine docker image is ready, we can use it to deploy a corresponding Rollups smart contract.
This requires you to specify the account and RPC gateway to use when submitting the deploy transaction on the target network, which can be done by defining the following environment variables:

```shell
export MNEMONIC=<user sequence of twelve words>
export RPC_URL=<https://your.rpc.gateway>
```

For example, to deploy to the Goerli testnet using an Alchemy RPC node, you could execute:

```shell
export MNEMONIC=<user sequence of twelve words>
export RPC_URL=https://eth-goerli.alchemyapi.io/v2/<USER_KEY>
```

With that in place, you can submit a deploy transaction to the Cartesi DApp Factory contract on the target network by executing the following command:

```shell
DAPP_NAME="voucher-trade-assets" docker compose --env-file env.<network> -f deploy-testnet.yml up
```

Here, `env.<network>` specifies general parameters for the target network, like its name and chain ID. In the case of Goerli, the command would be:

```shell
DAPP_NAME="voucher-trade-assets" docker compose --env-file env.goerli -f deploy-testnet.yml up
```

This will create a file at `deployments/<network>/voucher-trade-assets.json` with the deployed contract's address.
Once the command finishes, it is advisable to stop the docker compose and remove the volumes created when executing it.

```shell
DAPP_NAME="voucher-trade-assets" docker compose --env-file env.<network> -f deploy-testnet.yml down -v
```

After that, a corresponding Cartesi Validator Node must also be instantiated in order to interact with the deployed smart contract on the target network and handle the back-end logic of the DApp.
Aside from the environment variables defined before, the node will also need a secure websocket endpoint for the RPC gateway (WSS URL).

For example, for Goerli and Alchemy, you would set the following additional variable:

```shell
export WSS_URL=wss://eth-goerli.alchemyapi.io/v2/<USER_KEY>
```

Then, the node itself can be started by running a docker compose as follows:

```shell
DAPP_NAME="voucher-trade-assets" docker compose --env-file env.<network> -f docker-compose-testnet.yml -f docker-compose.override.yml up
```

Alternatively, you can also run the node on host mode by executing:

```shell
DAPP_NAME="voucher-trade-assets" docker compose --env-file env.<network> -f docker-compose-testnet.yml -f docker-compose.override.yml -f docker-compose-host-testnet.yml up
```

## Running the back-end in host mode

When developing an application, it is often important to easily test and debug it. For that matter, it is possible to run the Cartesi Rollups environment in [host mode](https://github.com/cartesi/rollups-examples/tree/main/README.md#host-mode), so that the DApp's back-end can be executed directly on the host machine, allowing it to be debugged using regular development tools such as an IDE.

The host environment can be executed with the following command:

```shell
docker compose -f docker-compose.yml -f docker-compose.override.yml -f docker-compose-host.yml up
```

This DApp's back-end is written in Python, so to run it in your machine you need to have `python3` installed.

In order to start the back-end, run the following commands in a dedicated terminal:

```shell
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" python3 voucher-trade-assets.py
```

The final command will effectively run the back-end and send corresponding outputs to port `5004`.
It can optionally be configured in an IDE to allow interactive debugging using features like breakpoints.

You can also use a tool like [entr](https://eradman.com/entrproject/) to restart the back-end automatically when the code changes. For example:

```shell
ls *.py | ROLLUP_HTTP_SERVER_URL="http://127.0.0.1:5004" entr -r python3 voucher-trade-assets.py
```

After the back-end successfully starts, it should print an output like the following:

```log
INFO:__main__:HTTP rollup_server url is http://127.0.0.1:5004
INFO:__main__:Sending finish
```

After that, you can interact with the application normally [as explained above](#interacting-with-the-application).


## Interacting with the DApp

After the `voucher-trade-assets` contract was deployed and the Cartesi Node is running the application is ready and users can finally interact with it. The procedure for interacting is as follows:

1. On Remix IDE, execute the `set_dapp_address` method of the `voucher-trade-assets` contract to set the rollup contract address. This step is to allow the layer-1 contract to send inputs to the Cartesi Rollups.
2. Execute the `play` method passing the opponent's address to challenge him for a coin toss game.
3. The challenged player executes the same `play` method passing the challenger address. The input is then fetched by the Cartesi Node the coin toss is executed inside the Cartesi Machine. A notice and a voucher are generated.
4. (Optional) Check the notice and the voucher using the [frontend-console](https://github.com/cartesi/rollups-examples/tree/main/frontend-console).
5. Wait for the dispute period to end to execute the voucher. The dispute period is set to 5 minutes in testnet^, as can be seen in `deploy-testnet.yml`. If running locally advance the time with the following command:
```shell
curl --data '{"id":1337,"jsonrpc":"2.0","method":"evm_increaseTime","params":[864010]}' http://localhost:8545
```
6. Execute the voucher using the `frontend-console`.
7. (Optional) Check the value of the `last_game` variable in the `voucher-trade-assets` smart contract to see the persisted result in layer-1 due to the voucher execution.

^ **This value was chosen for testing purposes, do not use it in production!!!** The default value is 1 week.