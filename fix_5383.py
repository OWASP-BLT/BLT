// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract DumpedToken is IERC20, Ownable, ReentrancyGuard {
    string public constant name = "Dumped Token";
    string public constant symbol = "DUMP";
    uint8 public constant decimals = 18;
    
    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;
    
    // Anti-dump mechanism
    uint256 public maxTransactionAmount;
    uint256 public maxWalletAmount;
    uint256 public cooldownPeriod;
    mapping(address => uint256) private _lastTransactionTime;
    
    // Fee structure
    uint256 public buyFee = 2; // 2%
    uint256 public sellFee = 3; // 3%
    address public feeWallet;
    
    // Blacklist
    mapping(address => bool) public blacklisted;
    
    // Excluded from fees
    mapping(address => bool) public excludedFromFees;
    
    event MaxTransactionAmountUpdated(uint256 amount);
    event MaxWalletAmountUpdated(uint256 amount);
    event CooldownPeriodUpdated(uint256 period);
    event Blacklisted(address indexed account, bool status);
    event FeeWalletUpdated(address indexed wallet);
    event FeesUpdated(uint256 buyFee, uint256 sellFee);
    
    constructor() {
        _totalSupply = 1_000_000_000 * 10**decimals; // 1 billion tokens
        _balances[msg.sender] = _totalSupply;
        
        maxTransactionAmount = _totalSupply / 100; // 1% of supply
        maxWalletAmount = _totalSupply / 50; // 2% of supply
        cooldownPeriod = 60 seconds;
        feeWallet = msg.sender;
        
        excludedFromFees[msg.sender] = true;
        excludedFromFees[address(this)] = true;
        
        emit Transfer(address(0), msg.sender, _totalSupply);
    }
    
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address to, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address from, address to, uint256 amount) external override returns (bool) {
        _spendAllowance(from, msg.sender, amount);
        _transfer(from, to, amount);
        return true;
    }
    
    function _transfer(address from, address to, uint256 amount) private {
        require(from != address(0), "Transfer from zero address");
        require(to != address(0), "Transfer to zero address");
        require(!blacklisted[from] && !blacklisted[to], "Blacklisted address");
        require(amount > 0, "Transfer amount must be greater than zero");
        
        // Anti-dump checks
        if (from != owner() && to != owner()) {
            require(amount <= maxTransactionAmount, "Exceeds max transaction amount");
            
            if (to != address(this) && to != feeWallet) {
                require(balanceOf(to) + amount <= maxWalletAmount, "Exceeds max wallet amount");
            }
            
            require(
                block.timestamp >= _lastTransactionTime[from] + cooldownPeriod,
                "Cooldown period not elapsed"
            );
        }
        
        // Calculate fees
        uint256 fee = 0;
        if (!excludedFromFees[from] && !excludedFromFees[to]) {
            if (to == address(this)) {
                fee = (amount * sellFee) / 100;
            } else if (from == address(this)) {
                fee = (amount * buyFee) / 100;
            }
        }
        
        uint256 transferAmount = amount - fee;
        
        _balances[from] -= amount;
        _balances[to] += transferAmount;
        
        if (fee > 0) {
            _balances[feeWallet] += fee;
            emit Transfer(from, feeWallet, fee);
        }
        
        _lastTransactionTime[from] = block.timestamp;
        _lastTransactionTime[to] = block.timestamp;
        
        emit Transfer(from, to, transferAmount);
    }
    
    function _approve(address owner, address spender, uint256 amount) private {
        require(owner != address(0), "Approve from zero address");
        require(spender != address(0), "Approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    function _spendAllowance(address owner, address spender, uint256 amount) private {
        uint256 currentAllowance = _allowances[owner][spender];
        if (currentAllowance != type(uint256).max) {
            require(currentAllowance >= amount, "Insufficient allowance");
            _approve(owner, spender, currentAllowance - amount);
        }
    }
    
    // Admin functions
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
    
    function setBlacklisted(address account, bool status) external onlyOwner {
        blacklisted[account] = status;
        emit Blacklisted(account, status);
    }
    
    function setFeeWallet(address wallet) external onlyOwner {
        require(wallet != address(0), "Invalid wallet address");
        feeWallet = wallet;
        emit FeeWalletUpdated(wallet);
    }
    
    function setFees(uint256 _buyFee, uint256 _sellFee) external onlyOwner {
        require(_buyFee <= 10 && _sellFee <= 10, "Fees too high");
        buyFee = _buyFee;
        sellFee = _sellFee;
        emit FeesUpdated(_buyFee, _sellFee);
    }
    
    function setExcludedFromFees(address account, bool status) external onlyOwner {
        excludedFromFees[account] = status;
    }
    
    // Emergency withdraw
    function withdrawTokens(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(msg.sender, amount);
    }
    
    function withdrawNative() external onlyOwner {
        payable(msg.sender).transfer(address(this).balance);
    }
    
    receive() external payable {}
}
