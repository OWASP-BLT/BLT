// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

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
    
    // P2P escrow system
    struct Escrow {
        address seller;
        address buyer;
        uint256 amount;
        uint256 price;
        bool completed;
        bool disputed;
        uint256 timestamp;
    }
    
    mapping(uint256 => Escrow) public escrows;
    uint256 public escrowCount;
    
    // Fee structure
    uint256 public feePercent = 1; // 1% fee
    address public feeWallet;
    
    // Events
    event EscrowCreated(uint256 indexed escrowId, address indexed seller, address indexed buyer, uint256 amount, uint256 price);
    event EscrowCompleted(uint256 indexed escrowId);
    event EscrowDisputed(uint256 indexed escrowId);
    event EscrowRefunded(uint256 indexed escrowId);
    
    constructor(address _feeWallet) {
        require(_feeWallet != address(0), "Invalid fee wallet");
        feeWallet = _feeWallet;
        _mint(msg.sender, 1000000 * 10**decimals); // Initial supply
    }
    
    function totalSupply() external view override returns (uint256) {
        return _totalSupply;
    }
    
    function balanceOf(address account) external view override returns (uint256) {
        return _balances[account];
    }
    
    function transfer(address recipient, uint256 amount) external override returns (bool) {
        _transfer(msg.sender, recipient, amount);
        return true;
    }
    
    function allowance(address owner, address spender) external view override returns (uint256) {
        return _allowances[owner][spender];
    }
    
    function approve(address spender, uint256 amount) external override returns (bool) {
        _approve(msg.sender, spender, amount);
        return true;
    }
    
    function transferFrom(address sender, address recipient, uint256 amount) external override returns (bool) {
        uint256 currentAllowance = _allowances[sender][msg.sender];
        require(currentAllowance >= amount, "ERC20: transfer amount exceeds allowance");
        _approve(sender, msg.sender, currentAllowance - amount);
        _transfer(sender, recipient, amount);
        return true;
    }
    
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "ERC20: transfer from zero address");
        require(recipient != address(0), "ERC20: transfer to zero address");
        require(_balances[sender] >= amount, "ERC20: transfer amount exceeds balance");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        emit Transfer(sender, recipient, amount);
    }
    
    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "ERC20: mint to zero address");
        _totalSupply += amount;
        _balances[account] += amount;
        emit Transfer(address(0), account, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from zero address");
        require(spender != address(0), "ERC20: approve to zero address");
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    // P2P Escrow Functions
    function createEscrow(address buyer, uint256 amount, uint256 price) external nonReentrant returns (uint256) {
        require(buyer != address(0), "Invalid buyer address");
        require(amount > 0, "Amount must be greater than 0");
        require(price > 0, "Price must be greater than 0");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        
        escrowCount++;
        escrows[escrowCount] = Escrow({
            seller: msg.sender,
            buyer: buyer,
            amount: amount,
            price: price,
            completed: false,
            disputed: false,
            timestamp: block.timestamp
        });
        
        _transfer(msg.sender, address(this), amount);
        emit EscrowCreated(escrowCount, msg.sender, buyer, amount, price);
        return escrowCount;
    }
    
    function completeEscrow(uint256 escrowId) external nonReentrant {
        Escrow storage escrow = escrows[escrowId];
        require(msg.sender == escrow.buyer, "Only buyer can complete");
        require(!escrow.completed, "Already completed");
        require(!escrow.disputed, "Escrow is disputed");
        
        escrow.completed = true;
        
        // Calculate fee
        uint256 fee = (escrow.amount * feePercent) / 100;
        uint256 sellerAmount = escrow.amount - fee;
        
        // Transfer to seller and fee wallet
        _transfer(address(this), escrow.seller, sellerAmount);
        if (fee > 0) {
            _transfer(address(this), feeWallet, fee);
        }
        
        emit EscrowCompleted(escrowId);
    }
    
    function disputeEscrow(uint256 escrowId) external {
        Escrow storage escrow = escrows[escrowId];
        require(msg.sender == escrow.buyer || msg.sender == escrow.seller, "Not party to escrow");
        require(!escrow.completed, "Already completed");
        require(!escrow.disputed, "Already disputed");
        
        escrow.disputed = true;
        emit EscrowDisputed(escrowId);
    }
    
    function refundEscrow(uint256 escrowId) external onlyOwner {
        Escrow storage escrow = escrows[escrowId];
        require(escrow.disputed, "Escrow not disputed");
        require(!escrow.completed, "Already completed");
        
        escrow.completed = true;
        _transfer(address(this), escrow.buyer, escrow.amount);
        emit EscrowRefunded(escrowId);
    }
    
    function setFeePercent(uint256 _feePercent) external onlyOwner {
        require(_feePercent <= 10, "Fee too high");
        feePercent = _feePercent;
    }
    
    function setFeeWallet(address _feeWallet) external onlyOwner {
        require(_feeWallet != address(0), "Invalid address");
        feeWallet = _feeWallet;
    }
    
    // Fallback function to receive TRX/ETH
    receive() external payable {}
}
