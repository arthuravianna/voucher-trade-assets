// SPDX-License-Identifier: MIT
pragma solidity >=0.6.0 <0.9.0;

import "@cartesi/rollups@0.8.2/contracts/interfaces/IERC20Portal.sol";

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";

// Core
import "@uniswap/v2-core/contracts/interfaces/IUniswapV2Factory.sol";
import "@uniswap/v2-core/contracts/interfaces/IUniswapV2Pair.sol";
import "@uniswap/v2-core/contracts/interfaces/IUniswapV2ERC20.sol";

// Periphery (Router)
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router01.sol";
import "@uniswap/v2-periphery/contracts/interfaces/IUniswapV2Router02.sol";

contract TradeAssetsUniswapV2 {
    address deployer;
    address L2_DAPP;

    // https://docs.uniswap.org/contracts/v2/reference/smart-contracts/factory
    IUniswapV2Factory internal uniswapV2Factory = IUniswapV2Factory(0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f);

    // https://docs.uniswap.org/contracts/v2/reference/smart-contracts/router-02
    IUniswapV2Router02 internal uniswapV2Router = IUniswapV2Router02(0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D);


    constructor() {
        deployer = msg.sender;
    }

    function set_dapp_address(address l2_dapp) public {
        require(msg.sender == deployer);

        L2_DAPP = l2_dapp;
    }

    function rollupSwap(address erc20, uint256 swap_amount, address desiredToken) public {
        require(L2_DAPP != address(0), "Must set Rollups address first.");
        
        IERC20 token = IERC20(erc20);

        // transfer the tokens to this contract to use the assets
        require(token.transferFrom(msg.sender, address(this), swap_amount), "ERC20 transferFrom failed");
        
        bytes memory data = abi.encode(address(this), desiredToken);
        IERC20Portal(L2_DAPP).erc20Deposit(erc20, swap_amount, data);
    }

    function executeSwap(address depositedToken, uint amountIn, address to, address desiredToken) public {
        require(msg.sender == L2_DAPP, "Only the Cartesi DApp can execute the swap.");

        require(IUniswapV2ERC20(depositedToken).approve(address(uniswapV2Router), amountIn), "approve failed.");

        // get pool's address
        address pair = uniswapV2Factory.getPair(desiredToken, depositedToken);

        // get each token reserves in the pool
        (uint112 tkAReserves, uint112 tkBReserves, ) = IUniswapV2Pair(pair).getReserves();
        
        // asks how many token B the user can get if he sells "amountIn" of token A
        uint amountOutMin = uniswapV2Router.quote(amountIn, tkAReserves, tkBReserves);

        require(amountOutMin > 0, "Amount has to be bigger than 0.");

        address[] memory path = new address[](2);
        path[0] = desiredToken;
        path[1] = depositedToken;

        uniswapV2Router.swapExactTokensForTokens(
            amountIn,
            amountOutMin,
            path,
            to,
            2000000000 // deadline (EPOCH)
        );
    }
}