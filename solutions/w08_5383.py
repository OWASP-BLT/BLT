// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is ERC20, Ownable, ReentrancyGuard {
    // Events
    event TokensDumped(address indexed user, uint256 amount);
    event RewardClaimed(address indexed user, uint256 amount);
    event LiquidityAdded(uint256 amount);
    
    // State variables
    uint256 public constant MAX_SUPPLY = 1000000 * 10**18; // 1 million tokens
    uint256 public constant DUMP_FEE = 25; // 0.25% fee
    uint256 public constant REWARD_POOL = 50000 * 10**18; // 50k tokens for rewards
    
    mapping(address => uint256) public lastDumpTime;
    mapping(address => uint256) public userRewards;
    uint256 public totalDumped;
    uint256 public rewardBalance;
    
    constructor() ERC20("Dumped Token", "DUMP") {
        _mint(msg.sender, MAX_SUPPLY);
        rewardBalance = REWARD_POOL;
    }
    
    function dump(uint256 amount) external nonReentrant {
        require(amount > 0, "Amount must be greater than 0");
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        require(block.timestamp >= lastDumpTime[msg.sender] + 1 days, "Cooldown active");
        
        uint256 fee = (amount * DUMP_FEE) / 10000;
        uint256 netAmount = amount - fee;
        
        _transfer(msg.sender, address(this), amount);
        _burn(address(this), netAmount);
        
        // Add fee to reward pool
        rewardBalance += fee;
        
        // Update state
        lastDumpTime[msg.sender] = block.timestamp;
        totalDumped += netAmount;
        
        // Calculate and assign rewards
        uint256 reward = (fee * 10) / 100; // 10% of fee goes to user
        userRewards[msg.sender] += reward;
        rewardBalance -= reward;
        
        emit TokensDumped(msg.sender, netAmount);
    }
    
    function claimRewards() external nonReentrant {
        uint256 reward = userRewards[msg.sender];
        require(reward > 0, "No rewards to claim");
        require(rewardBalance >= reward, "Insufficient reward pool");
        
        userRewards[msg.sender] = 0;
        rewardBalance -= reward;
        _transfer(address(this), msg.sender, reward);
        
        emit RewardClaimed(msg.sender, reward);
    }
    
    function addLiquidity(uint256 amount) external onlyOwner {
        require(amount > 0, "Amount must be greater than 0");
        require(balanceOf(address(this)) >= amount, "Insufficient contract balance");
        
        _transfer(address(this), msg.sender, amount);
        emit LiquidityAdded(amount);
    }
    
    function getDumpInfo(address user) external view returns (
        uint256 lastDump,
        uint256 rewards,
        uint256 balance,
        bool canDump
    ) {
        return (
            lastDumpTime[user],
            userRewards[user],
            balanceOf(user),
            block.timestamp >= lastDumpTime[user] + 1 days
        );
    }
    
    function getContractInfo() external view returns (
        uint256 totalSupply,
        uint256 totalDumpedAmount,
        uint256 rewardPoolBalance,
        uint256 contractBalance
    ) {
        return (
            totalSupply(),
            totalDumped,
            rewardBalance,
            balanceOf(address(this))
        );
    }
}
