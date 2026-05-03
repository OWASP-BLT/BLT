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
    
    // P2P features
    struct P2POrder {
        address seller;
        address tokenAddress;
        uint256 amount;
        uint256 price; // in USDT (6 decimals)
        bool isActive;
        uint256 timestamp;
    }
    
    mapping(uint256 => P2POrder) public p2pOrders;
    uint256 public orderCounter;
    
    // Fee structure
    uint256 public platformFee = 25; // 0.25% (basis points)
    address public feeWallet = 0x742d35Cc6634C0532925a3b844Bc454e4438f44e;
    
    // Events
    event OrderCreated(uint256 indexed orderId, address indexed seller, uint256 amount, uint256 price);
    event OrderFilled(uint256 indexed orderId, address indexed buyer, uint256 amount);
    event OrderCancelled(uint256 indexed orderId);
    
    constructor() {
        _totalSupply = 1000000 * 10**18; // 1 million tokens
        _balances[msg.sender] = _totalSupply;
        emit Transfer(address(0), msg.sender, _totalSupply);
    }
    
    // ERC20 implementation
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
        _transfer(sender, recipient, amount);
        require(_allowances[sender][msg.sender] >= amount, "ERC20: insufficient allowance");
        _approve(sender, msg.sender, _allowances[sender][msg.sender] - amount);
        return true;
    }
    
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "ERC20: transfer from zero address");
        require(recipient != address(0), "ERC20: transfer to zero address");
        require(_balances[sender] >= amount, "ERC20: insufficient balance");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        emit Transfer(sender, recipient, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "ERC20: approve from zero address");
        require(spender != address(0), "ERC20: approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    // P2P Order functions
    function createP2POrder(uint256 amount, uint256 price) external {
        require(amount > 0, "Amount must be greater than 0");
        require(price > 0, "Price must be greater than 0");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        
        _transfer(msg.sender, address(this), amount);
        
        orderCounter++;
        p2pOrders[orderCounter] = P2POrder({
            seller: msg.sender,
            tokenAddress: address(this),
            amount: amount,
            price: price,
            isActive: true,
            timestamp: block.timestamp
        });
        
        emit OrderCreated(orderCounter, msg.sender, amount, price);
    }
    
    function fillP2POrder(uint256 orderId) external payable nonReentrant {
        P2POrder storage order = p2pOrders[orderId];
        require(order.isActive, "Order is not active");
        require(msg.sender != order.seller, "Cannot fill your own order");
        
        uint256 totalCost = (order.amount * order.price) / 10**18;
        uint256 fee = (totalCost * platformFee) / 10000;
        uint256 sellerAmount = totalCost - fee;
        
        require(msg.value >= totalCost, "Insufficient payment");
        
        // Transfer tokens to buyer
        _transfer(address(this), msg.sender, order.amount);
        
        // Pay seller
        payable(order.seller).transfer(sellerAmount);
        
        // Pay fee
        payable(feeWallet).transfer(fee);
        
        // Refund excess payment
        if (msg.value > totalCost) {
            payable(msg.sender).transfer(msg.value - totalCost);
        }
        
        order.isActive = false;
        emit OrderFilled(orderId, msg.sender, order.amount);
    }
    
    function cancelP2POrder(uint256 orderId) external {
        P2POrder storage order = p2pOrders[orderId];
        require(order.seller == msg.sender, "Not the seller");
        require(order.isActive, "Order is not active");
        
        _transfer(address(this), msg.sender, order.amount);
        order.isActive = false;
        
        emit OrderCancelled(orderId);
    }
    
    // Admin functions
    function setPlatformFee(uint256 newFee) external onlyOwner {
        require(newFee <= 1000, "Fee too high"); // Max 10%
        platformFee = newFee;
    }
    
    function setFeeWallet(address newWallet) external onlyOwner {
        require(newWallet != address(0), "Invalid address");
        feeWallet = newWallet;
    }
    
    // Fallback function
    receive() external payable {}
}
