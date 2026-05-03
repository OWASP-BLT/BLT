// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

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
    
    // P2P trading features
    struct Order {
        address seller;
        address buyer;
        uint256 amount;
        uint256 price;
        bool isActive;
        uint256 timestamp;
    }
    
    Order[] public orders;
    mapping(address => uint256[]) public userOrders;
    
    // Fee structure
    uint256 public tradingFee = 25; // 0.25% in basis points
    address public feeWallet;
    
    // Events
    event OrderCreated(uint256 indexed orderId, address indexed seller, uint256 amount, uint256 price);
    event OrderFilled(uint256 indexed orderId, address indexed buyer, address indexed seller, uint256 amount);
    event OrderCancelled(uint256 indexed orderId);
    event FeeUpdated(uint256 newFee);
    event FeeWalletUpdated(address newWallet);
    
    constructor(address _feeWallet) {
        require(_feeWallet != address(0), "Invalid fee wallet");
        feeWallet = _feeWallet;
        _mint(msg.sender, 1000000 * 10**18); // Initial supply: 1M tokens
    }
    
    // ERC20 Implementation
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
        _approve(sender, msg.sender, _allowances[sender][msg.sender] - amount);
        return true;
    }
    
    // P2P Trading Functions
    function createOrder(uint256 amount, uint256 price) external nonReentrant {
        require(amount > 0, "Amount must be greater than 0");
        require(price > 0, "Price must be greater than 0");
        require(_balances[msg.sender] >= amount, "Insufficient balance");
        
        _transfer(msg.sender, address(this), amount);
        
        uint256 orderId = orders.length;
        orders.push(Order({
            seller: msg.sender,
            buyer: address(0),
            amount: amount,
            price: price,
            isActive: true,
            timestamp: block.timestamp
        }));
        
        userOrders[msg.sender].push(orderId);
        
        emit OrderCreated(orderId, msg.sender, amount, price);
    }
    
    function fillOrder(uint256 orderId) external payable nonReentrant {
        require(orderId < orders.length, "Order does not exist");
        Order storage order = orders[orderId];
        require(order.isActive, "Order is not active");
        require(msg.sender != order.seller, "Cannot fill own order");
        require(msg.value >= order.amount * order.price / 1e18, "Insufficient payment");
        
        // Calculate fee
        uint256 fee = (order.amount * tradingFee) / 10000;
        uint256 sellerAmount = order.amount - fee;
        
        // Transfer tokens to buyer
        _transfer(address(this), msg.sender, order.amount);
        
        // Transfer payment to seller
        uint256 payment = order.amount * order.price / 1e18;
        uint256 sellerPayment = payment - (payment * tradingFee / 10000);
        
        (bool success, ) = payable(order.seller).call{value: sellerPayment}("");
        require(success, "Payment to seller failed");
        
        // Transfer fee to fee wallet
        (success, ) = payable(feeWallet).call{value: payment - sellerPayment}("");
        require(success, "Fee transfer failed");
        
        // Update order
        order.isActive = false;
        order.buyer = msg.sender;
        
        emit OrderFilled(orderId, msg.sender, order.seller, order.amount);
    }
    
    function cancelOrder(uint256 orderId) external nonReentrant {
        require(orderId < orders.length, "Order does not exist");
        Order storage order = orders[orderId];
        require(order.seller == msg.sender, "Not the seller");
        require(order.isActive, "Order is not active");
        
        order.isActive = false;
        _transfer(address(this), msg.sender, order.amount);
        
        emit OrderCancelled(orderId);
    }
    
    function getOrders() external view returns (Order[] memory) {
        return orders;
    }
    
    function getUserOrders(address user) external view returns (uint256[] memory) {
        return userOrders[user];
    }
    
    // Admin functions
    function setTradingFee(uint256 _fee) external onlyOwner {
        require(_fee <= 1000, "Fee too high"); // Max 10%
        tradingFee = _fee;
        emit FeeUpdated(_fee);
    }
    
    function setFeeWallet(address _wallet) external onlyOwner {
        require(_wallet != address(0), "Invalid wallet");
        feeWallet = _wallet;
        emit FeeWalletUpdated(_wallet);
    }
    
    function withdrawTokens(address token, uint256 amount) external onlyOwner {
        IERC20(token).transfer(msg.sender, amount);
    }
    
    // Internal functions
    function _transfer(address sender, address recipient, uint256 amount) internal {
        require(sender != address(0), "Transfer from zero address");
        require(recipient != address(0), "Transfer to zero address");
        require(_balances[sender] >= amount, "Insufficient balance");
        
        _balances[sender] -= amount;
        _balances[recipient] += amount;
        
        emit Transfer(sender, recipient, amount);
    }
    
    function _mint(address account, uint256 amount) internal {
        require(account != address(0), "Mint to zero address");
        
        _totalSupply += amount;
        _balances[account] += amount;
        
        emit Transfer(address(0), account, amount);
    }
    
    function _approve(address owner, address spender, uint256 amount) internal {
        require(owner != address(0), "Approve from zero address");
        require(spender != address(0), "Approve to zero address");
        
        _allowances[owner][spender] = amount;
        emit Approval(owner, spender, amount);
    }
    
    // Receive function for ETH
    receive() external payable {}
}
