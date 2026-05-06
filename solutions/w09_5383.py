// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is IERC20, Ownable, ReentrancyGuard {
    string public constant name = "Dumped Token";
    string public constant symbol = "DUMPED";
    uint8 public constant decimals = 18;
    uint256 private _totalSupply;
    
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // Anti-dump mechanism
    uint256 public constant MAX_TRANSACTION_PERCENT = 1; // 1% max per transaction
    uint256 public constant COOLDOWN_PERIOD = 1 hours;
    mapping(address => uint256) private _lastTransferTime;
    
    // Fee mechanism
    uint256 public constant BURN_FEE = 1; // 1% burn fee
    uint256 public constant REWARD_FEE = 1; // 1% reward fee
    address public rewardPool;
    
    event RewardPoolUpdated(address indexed newPool);
    
    constructor(uint256 initialSupply) {
        _totalSupply = initialSupply * 10**decimals;
        _balances[owner()] = _totalSupply;
        rewardPool = address(this);
        emit Transfer(address(0), owner(), _totalSupply);
    }
    
    modifier antiDump(address sender, uint256 amount) {
        if (sender != owner() && sender != address(this)) {
            require(
                amount <= (_totalSupply * MAX_TRANSACTION_PERCENT) / 100,
                "Dumped: Transaction exceeds max limit"
            );
            require(
                block.timestamp >= _lastTransferTime[sender] + COOLDOWN_PERIOD,
                "Dumped: Cooldown period not elapsed"
            );
        }
        _;
    }
    
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address recipient, uint256 amount) 
        external 
        override 
        nonReentrant 
        antiDump(msg.sender, amount) 
        returns (bool) 
    {
        _transfer(msg.sender, recipient, amount);
        return true;
    }
    
    function allowance(address owner, address spender) 
        external 
        view 
        override 
        returns (uint256) 
    {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) 
        external 
        override 
        returns (bool) 
    {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address sender, address recipient, uint256 amount) 
        external 
        override 
        nonReentrant 
        antiDump(sender, amount) 
        returns (bool) 
    {
        require(
            _allowances[sender][msg.sender] >= amount,
            "Dumped: Insufficient allowance"
        );
        _allowances[sender][msg.sender] -= amount;
        _transfer(sender, recipient, amount);
        return true;
    }
    
    function _transfer(address sender, address recipient, uint256 amount) 
        private 
    {
        require(sender != address(0), "Dumped: Transfer from zero address");
        require(recipient != address(0), "Dumped: Transfer to zero address");
        require(_balances[sender] >= amount, "Dumped: Insufficient balance");
        
        uint256 burnAmount = (amount * BURN_FEE) / 100;
        uint256 rewardAmount = (amount * REWARD_FEE) / 100;
        uint256 transferAmount = amount - burnAmount - rewardAmount;
        
        _balances[sender] -= amount;
        _balances[recipient] += transferAmount;
        
        // Burn tokens
        if (burnAmount > 0) {
            _totalSupply -= burnAmount;
            emit Transfer(sender, address(0), burnAmount);
        }
        
        // Send reward fee to pool
        if (rewardAmount > 0) {
            _balances[rewardPool] += rewardAmount;
            emit Transfer(sender, rewardPool, rewardAmount);
        }
        
        _lastTransferTime[sender] = block.timestamp;
        _lastTransferTime[recipient] = block.timestamp;
        
        emit Transfer(sender, recipient, transferAmount);
    }
    
    function updateRewardPool(address newPool) external onlyOwner {
        require(newPool != address(0), "Dumped: Invalid pool address");
        rewardPool = newPool;
        emit RewardPoolUpdated(newPool);
    }
    
    // Allow contract to receive ETH for rewards
    receive() external payable {}
    
    // Distribute rewards from pool
    function distributeRewards(address[] calldata recipients, uint256[] calldata amounts) 
        external 
        onlyOwner 
    {
        require(recipients.length == amounts.length, "Dumped: Array length mismatch");
        uint256 totalRewards = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalRewards += amounts[i];
        }
        require(_balances[rewardPool] >= totalRewards, "Dumped: Insufficient rewards");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            _balances[rewardPool] -= amounts[i];
            _balances[recipients[i]] += amounts[i];
            emit Transfer(rewardPool, recipients[i], amounts[i]);
        }
    }
}
