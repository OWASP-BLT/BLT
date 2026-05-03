// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is IERC20, Ownable, ReentrancyGuard {
    string public name = "Dumped Token";
    string public symbol = "DUMP";
    uint8 public decimals = 18;
    uint256 private _totalSupply;
    
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // Anti-dump mechanism
    uint256 public maxTransactionAmount;
    uint256 public maxWalletAmount;
    uint256 public cooldownPeriod;
    mapping(address => uint256) private _lastTransaction;
    
    event MaxTransactionAmountUpdated(uint256 amount);
    event MaxWalletAmountUpdated(uint256 amount);
    event CooldownPeriodUpdated(uint256 period);
    
    constructor(uint256 initialSupply) {
        _totalSupply = initialSupply * 10**decimals;
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
        
        // Initialize anti-dump parameters
        maxTransactionAmount = _totalSupply / 100; // 1% of total supply
        maxWalletAmount = _totalSupply / 50; // 2% of total supply
        cooldownPeriod = 60 seconds;
    }
    
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address recipient, uint256 amount) external override nonReentrant returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address sender, address recipient, uint256 amount) external override nonReentrant returns (bool) {
        require(_allowances[sender][msg.sender] >= amount, "ERC20: insufficient allowance");
        _allowances[sender][msg.sender] -= amount;
        _transfer(sender, recipient, amount);
        return true;
    }
    
    function _transfer(address sender, address recipient, uint256 amount) private {
        require(sender != address(0), "ERC20: transfer from zero address");
        require(recipient != address(0), "ERC20: transfer to zero address");
        require(amount > 0, "ERC20: transfer amount must be greater than zero");
        require(_balances[sender] >= amount, "ERC20: insufficient balance");
        
        // Anti-dump checks
        require(amount <= maxTransactionAmount, "Transfer amount exceeds max transaction limit");
        
        if (recipient != owner() && recipient != address(this)) {
            require(_balances[recipient] + amount <= maxWalletAmount, "Recipient wallet would exceed max wallet limit");
        }
        
        // Cooldown check
        require(block.timestamp >= _lastTransaction[sender] + cooldownPeriod, "Cooldown period not elapsed");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        _lastTransaction[sender] = block.timestamp;
        
        emit Transfer(sender, recipient, amount);
    }
    
    // Owner functions to adjust parameters
    function setMaxTransactionAmount(uint256 amount) external onlyOwner {
        maxTransactionAmount = amount;
        emit MaxTransactionAmountUpdated(amount);
    }
    
    function setMaxWalletAmount(uint256 amount) external onlyOwner {
        maxWalletAmount = amount;
        emit MaxWalletAmountUpdated(amount);
    }
    
    function setCooldownPeriod(uint256 period) external onlyOwner {
        cooldownPeriod = period;
        emit CooldownPeriodUpdated(period);
    }
    
    // Emergency function to pause transfers
    bool public paused = false;
    
    modifier whenNotPaused() {
        require(!paused, "Transfers are paused");
        _;
    }
    
    function pause() external onlyOwner {
        paused = true;
    }
    
    function unpause() external onlyOwner {
        paused = false;
    }
    
    // Override transfer functions with pause check
    function transfer(address recipient, uint256 amount) external override whenNotPaused nonReentrant returns (bool) {
        return super.transfer(recipient, amount);
    }
    
    function transferFrom(address sender, address recipient, uint256 amount) external override whenNotPaused nonReentrant returns (bool) {
        return super.transferFrom(sender, recipient, amount);
    }
}
